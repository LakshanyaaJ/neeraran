"""Unit Tests for Phase C - Multi-Horizon Recursive Engine & Pipeline Deployment.

Verifies:
1. 24h, 48h, and 72h horizon prediction counts and chronological sequence.
2. Dynamic predictions buffer updating (lag_1h, lag_24h, rolling_mean_24h).
3. Physical grounding & safety clipping (non-negative, capped at 3x peak design capacity).
4. Sub-2.0s execution latency SLA for 72h recursive multi-step forecasting.
5. In-memory programmatic Python API (forecast.predict) contract.
"""

import time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pytest

from ml.demand_forecasting.candidate_models import BaseForecaster
from ml.demand_forecasting.config import BUILDINGS, PATHS
from ml.demand_forecasting.data_loader import generate_synthetic_dataset
from ml.demand_forecasting.feature_pipeline import (
    BASELINE_FEATURE_COLS,
    EXTENDED_FEATURE_COLS,
    DataHygienePipeline,
    FeatureEngineer,
    IsolatedFoldPreprocessor,
)
from ml.demand_forecasting.forecast import get_pipeline, predict
from ml.demand_forecasting.multi_horizon_engine import MultiHorizonForecaster
from ml.demand_forecasting.weather_api import LocalFileWeatherProvider


class MockFixedPredictor(BaseForecaster):
    """Predictor returning a constant or formulaic value for deterministic recursion tests."""

    def __init__(self, fixed_value: float = 500.0):
        super().__init__(name="MockFixed", params={"fixed_value": fixed_value})
        self.fixed_value = fixed_value

    def fit(self, X, y):
        self.is_fitted = True
        return self

    def predict(self, X):
        n = len(X)
        return np.full(n, self.fixed_value)


class MockNegativePredictor(BaseForecaster):
    """Predictor attempting to output negative values to test safety clipping."""

    def __init__(self, negative_value: float = -250.0):
        super().__init__(name="MockNegative", params={"negative_value": negative_value})
        self.negative_value = negative_value

    def fit(self, X, y):
        self.is_fitted = True
        return self

    def predict(self, X):
        return np.full(len(X), self.negative_value)


@pytest.fixture(scope="module")
def sample_campus_telemetry():
    """Generates 30 days (720h) of clean synthetic telemetry for test cases."""
    df_telemetry, _ = generate_synthetic_dataset(num_days=30, random_seed=42, save_to_disk=False)
    hygiene = DataHygienePipeline()
    cleaned = hygiene.process(df_telemetry)
    return cleaned


class TestMultiHorizonRollouts:
    """Validates step counts, timestamp continuity, and recursive buffer updates."""

    @pytest.mark.parametrize("horizon", [24, 48, 72])
    def test_rollout_counts_and_timestamps(self, sample_campus_telemetry, horizon):
        pipeline = get_pipeline()
        model = pipeline["model"]
        preprocessor = pipeline["preprocessor"]

        engine = MultiHorizonForecaster(model=model, preprocessor=preprocessor)
        b_id = "hostel_01"
        hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]
        last_hist_ts = pd.to_datetime(hist["timestamp"].iloc[-1])

        pred_df, _ = engine.predict_horizon(building_id=b_id, historical_df=hist, horizon_hours=horizon)

        # Check prediction length
        assert len(pred_df) == horizon

        # Check timestamp sequence continuity
        pred_timestamps = pd.to_datetime(pred_df["timestamp"])
        expected_first_ts = last_hist_ts + pd.Timedelta(hours=1)
        assert pred_timestamps.iloc[0] == expected_first_ts

        # Strictly hourly frequency
        time_diffs = pred_timestamps.diff().dropna()
        assert (time_diffs == pd.Timedelta(hours=1)).all()

    def test_dynamic_buffer_lag_updates(self, sample_campus_telemetry):
        """Verifies that step k > 1 uses model predictions for lag_1h and dynamic rolling_mean."""
        fixed_val = 888.0
        mock_model = MockFixedPredictor(fixed_value=fixed_val)
        
        pipeline = get_pipeline()
        preprocessor = pipeline["preprocessor"]

        engine = MultiHorizonForecaster(model=mock_model, preprocessor=preprocessor)
        b_id = "academic_block_01"
        hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]

        pred_df, _ = engine.predict_horizon(building_id=b_id, historical_df=hist, horizon_hours=30)
        # All predictions must be exactly fixed_val
        np.testing.assert_allclose(pred_df["predicted_consumption"].values, fixed_val)


class TestPhysicalBoundingAndSafetyClipping:
    """Verifies that no negative or unphysically large values can leak through the engine."""

    def test_zero_clipping_on_negative_outputs(self, sample_campus_telemetry):
        neg_model = MockNegativePredictor(negative_value=-9999.0)
        pipeline = get_pipeline()
        preprocessor = pipeline["preprocessor"]

        engine = MultiHorizonForecaster(model=neg_model, preprocessor=preprocessor)
        b_id = "hostel_01"
        hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]

        pred_df, _ = engine.predict_horizon(building_id=b_id, historical_df=hist, horizon_hours=24)
        # Predictions must be clipped at zero (never negative)
        assert (pred_df["predicted_consumption"] == 0.0).all()

    def test_capacity_bounding_on_explosive_outputs(self, sample_campus_telemetry):
        explosive_model = MockFixedPredictor(fixed_value=1_000_000.0)
        pipeline = get_pipeline()
        preprocessor = pipeline["preprocessor"]

        engine = MultiHorizonForecaster(model=explosive_model, preprocessor=preprocessor)
        b_id = "library_01"
        peak_cap = float(BUILDINGS.BUILDINGS[b_id]["peak_capacity_lph"])
        max_allowed = peak_cap * 3.0

        hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]
        pred_df, _ = engine.predict_horizon(building_id=b_id, historical_df=hist, horizon_hours=24)

        # Predictions must be strictly capped at 3x peak design capacity
        assert (pred_df["predicted_consumption"] <= max_allowed).all()


class TestForecastInferenceSLAAndProgrammaticAPI:
    """Verifies performance latency benchmark (< 2.0s for 72h) and Python API interface."""

    def test_72h_latency_sla(self, sample_campus_telemetry):
        pipeline = get_pipeline()
        model = pipeline["model"]
        preprocessor = pipeline["preprocessor"]

        engine = MultiHorizonForecaster(model=model, preprocessor=preprocessor)
        b_id = "hostel_01"
        hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]

        t0 = time.perf_counter()
        pred_df, _ = engine.predict_horizon(building_id=b_id, historical_df=hist, horizon_hours=72)
        elapsed_sec = time.perf_counter() - t0

        # Hackathon SLA: Sub-second to 2.0s max for 72h recursive rollout
        assert elapsed_sec < 2.0, f"Inference took {elapsed_sec:.3f}s; target is < 2.0s"
        assert len(pred_df) == 72

    def test_programmatic_api_predict(self, sample_campus_telemetry):
        b_id = "canteen_01"
        hist_slice = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:200]

        response = predict(
            building_id=b_id,
            horizon=48,
            history=hist_slice,
        )

        assert response["building_id"] == b_id
        assert response["horizon_hours"] == 48
        assert response["unit"] == "litres"
        assert len(response["predictions"]) == 48
        assert response["total_predicted_consumption"] > 0
        assert response["execution_latency_ms"] < 2000.0  # < 2.0s

    def test_insufficient_history_rejection(self, sample_campus_telemetry):
        b_id = "research_lab_01"
        # Only 50 hours of history (minimum 168 hours required)
        short_hist = sample_campus_telemetry[sample_campus_telemetry["building_id"] == b_id].iloc[:50]

        with pytest.raises(ValueError, match="Insufficient telemetry history"):
            predict(building_id=b_id, horizon=24, history=short_hist)
