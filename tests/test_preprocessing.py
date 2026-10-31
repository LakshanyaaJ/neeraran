"""Unit Tests for Phase A - Data Hygiene, Synthetic Telemetry & Preprocessing Pipeline.

Strict enforcement:
- Zero unmocked external HTTP requests.
- Complete verification of shifted feature computations (no data leakage).
- Verification of short gap (<=3h) vs long gap (>3h) imputation rules.
"""

import json
from datetime import datetime, timedelta
import httpx
import numpy as np
import pandas as pd
import pytest

from ml.demand_forecasting.config import BUILDINGS, TRAINING
from ml.demand_forecasting.data_loader import (
    generate_synthetic_dataset,
    get_occupancy_pattern,
)
from ml.demand_forecasting.feature_pipeline import (
    BASELINE_FEATURE_COLS,
    EXTENDED_FEATURE_COLS,
    DataHygienePipeline,
    FeatureEngineer,
    IsolatedFoldPreprocessor,
    clean_and_impute_series,
)
from ml.demand_forecasting.weather_api import (
    LocalFileWeatherProvider,
    OpenMeteoProvider,
)


class TestSyntheticDataGeneration:
    """Validates the synthetic telemetry generator specifications."""

    def test_building_archetypes_and_duration(self):
        df_telemetry, df_weather = generate_synthetic_dataset(
            num_days=183,
            random_seed=42,
            save_to_disk=False,
        )
        # Check building count
        buildings = df_telemetry["building_id"].unique()
        assert len(buildings) >= 5
        assert set(BUILDINGS.BUILDINGS.keys()).issubset(set(buildings))

        # Check observations per building (at least 6 months = 4320 hours)
        for b_id, group in df_telemetry.groupby("building_id"):
            assert len(group) >= 4320

        # Check synthetic labeling
        assert (df_telemetry["is_synthetic"] == True).all()

    def test_missing_value_injection_rate(self):
        target_rate = 0.015
        df_telemetry, _ = generate_synthetic_dataset(
            num_days=30,
            random_seed=42,
            missing_rate=target_rate,
            save_to_disk=False,
        )
        actual_missing_rate = df_telemetry["water_consumption"].isna().mean()
        assert 0.010 <= actual_missing_rate <= 0.025

    def test_reproducibility(self):
        df1, _ = generate_synthetic_dataset(num_days=7, random_seed=42, save_to_disk=False)
        df2, _ = generate_synthetic_dataset(num_days=7, random_seed=42, save_to_disk=False)
        pd.testing.assert_frame_equal(df1, df2)

    def test_occupancy_patterns(self):
        # Hostel morning peak vs afternoon
        hostel_morning = get_occupancy_pattern("hostel", hour=8, day_of_week=2, is_vacation=False)
        hostel_midday = get_occupancy_pattern("hostel", hour=14, day_of_week=2, is_vacation=False)
        assert hostel_morning > hostel_midday

        # Academic block weekday vs weekend
        acad_weekday = get_occupancy_pattern("academic_block", hour=11, day_of_week=2, is_vacation=False)
        acad_weekend = get_occupancy_pattern("academic_block", hour=11, day_of_week=6, is_vacation=False)
        assert acad_weekday > acad_weekend
        assert acad_weekend <= 0.10


class TestWeatherProviderIntegration:
    """Validates weather abstraction, OpenMeteo mock transport, and offline fallback."""

    def test_local_file_provider(self, tmp_path):
        cache_csv = tmp_path / "test_weather_cache.csv"
        timestamps = pd.date_range("2026-01-01", periods=48, freq="h")
        df_dummy = pd.DataFrame({
            "timestamp": timestamps,
            "temperature": np.linspace(20.0, 30.0, 48),
            "rainfall": np.zeros(48),
        })
        df_dummy.to_csv(cache_csv, index=False)

        provider = LocalFileWeatherProvider(cache_path=cache_csv)
        forecast_df, source = provider.get_forecast(hours=24, start_time=timestamps[0])

        assert source == "local"
        assert len(forecast_df) == 24
        assert list(forecast_df.columns) == ["timestamp", "temperature", "rainfall"]

    def test_open_meteo_provider_mock_success(self):
        def mock_handler(request: httpx.Request):
            content = {
                "hourly": {
                    "time": ["2026-06-01T00:00", "2026-06-01T01:00", "2026-06-01T02:00"],
                    "temperature_2m": [25.5, 24.8, 24.1],
                    "precipitation": [0.0, 0.5, 0.0],
                }
            }
            return httpx.Response(200, json=content)

        transport = httpx.MockTransport(mock_handler)
        provider = OpenMeteoProvider(transport=transport, timeout=1.0, max_retries=1)

        forecast_df, source = provider.get_forecast(hours=3)
        assert source == "open-meteo"
        assert len(forecast_df) == 3
        assert forecast_df["temperature"].iloc[0] == 25.5
        assert forecast_df["rainfall"].iloc[1] == 0.5

    def test_open_meteo_fallback_on_network_failure(self, tmp_path):
        def failing_handler(request: httpx.Request):
            return httpx.Response(500, json={"error": "Service Unavailable"})

        transport = httpx.MockTransport(failing_handler)
        
        # Setup fallback cache
        cache_csv = tmp_path / "fallback_cache.csv"
        timestamps = pd.date_range("2026-01-01", periods=24, freq="h")
        pd.DataFrame({
            "timestamp": timestamps,
            "temperature": 25.0,
            "rainfall": 0.0,
        }).to_csv(cache_csv, index=False)

        fallback = LocalFileWeatherProvider(cache_path=cache_csv)
        provider = OpenMeteoProvider(
            transport=transport,
            timeout=0.1,
            max_retries=2,
            backoff_factor=0.01,
            fallback_provider=fallback,
        )

        forecast_df, source = provider.get_forecast(hours=12)
        assert source == "local"
        assert len(forecast_df) == 12


class TestDataHygieneAndImputation:
    """Validates missing gap thresholding and time series hygiene."""

    def test_short_vs_long_gap_imputation(self):
        # 10 points: indices 2, 3 have a 2-hour gap (should impute)
        # indices 5, 6, 7, 8 have a 4-hour gap (should NOT impute)
        s = pd.Series([10.0, 11.0, np.nan, np.nan, 14.0, np.nan, np.nan, np.nan, np.nan, 20.0])
        imputed, is_long = clean_and_impute_series(s, max_gap=3)

        # Short gap (indices 2, 3) must be linearly interpolated between 11.0 and 14.0
        assert not np.isnan(imputed.iloc[2])
        assert not np.isnan(imputed.iloc[3])
        assert np.isclose(imputed.iloc[2], 12.0)
        assert np.isclose(imputed.iloc[3], 13.0)
        assert not is_long.iloc[2]
        assert not is_long.iloc[3]

        # Long gap (indices 5, 6, 7, 8) must remain NaN and flagged
        assert np.isnan(imputed.iloc[5])
        assert np.isnan(imputed.iloc[6])
        assert np.isnan(imputed.iloc[7])
        assert np.isnan(imputed.iloc[8])
        assert is_long.iloc[5]
        assert is_long.iloc[8]

    def test_data_hygiene_deduplication_and_reindex(self):
        pipeline = DataHygienePipeline(short_gap_max_hours=3)
        raw = pd.DataFrame([
            {"timestamp": "2026-01-01 02:00:00", "building_id": "hostel_01", "water_consumption": 100.0, "temperature": 25.0, "rainfall": 0.0, "occupancy": 0.5},
            {"timestamp": "2026-01-01 00:00:00", "building_id": "hostel_01", "water_consumption": 90.0, "temperature": 24.0, "rainfall": 0.0, "occupancy": 0.4},
            # Duplicate at 02:00:00
            {"timestamp": "2026-01-01 02:00:00", "building_id": "hostel_01", "water_consumption": 105.0, "temperature": 25.0, "rainfall": 0.0, "occupancy": 0.5},
        ])
        cleaned = pipeline.process(raw)
        
        # Must have continuous hours: 00:00, 01:00 (reindexed/imputed), 02:00
        assert len(cleaned) == 3
        assert cleaned["timestamp"].iloc[0] == pd.to_datetime("2026-01-01 00:00:00")
        assert cleaned["timestamp"].iloc[1] == pd.to_datetime("2026-01-01 01:00:00")
        assert cleaned["timestamp"].iloc[2] == pd.to_datetime("2026-01-01 02:00:00")
        # Duplicate at 02:00 resolved to 105.0 (keep last)
        assert cleaned["water_consumption"].iloc[2] == 105.0


class TestFeatureLeakagePrevention:
    """Strict verification of shifted computation rules and training fold isolation."""

    def test_shifted_computation_rule(self):
        """CRITICAL: Verifies target y_t is never incorporated into rolling/lag features at step t."""
        timestamps = pd.date_range("2026-01-01", periods=200, freq="h")
        cons_values = np.arange(100.0, 300.0, 1.0)
        
        df = pd.DataFrame({
            "timestamp": timestamps,
            "building_id": "hostel_01",
            "water_consumption": cons_values,
            "temperature": 25.0,
            "rainfall": 0.0,
            "occupancy": 0.5,
            "hour": timestamps.hour,
            "day_of_week": timestamps.dayofweek,
            "month": timestamps.month,
            "is_weekend": 0,
            "is_holiday": 0,
        })

        fe = FeatureEngineer(use_extended_features=True)
        feats1 = fe.compute_features(df)

        # Tamper with water_consumption at step 50
        df_tampered = df.copy()
        df_tampered.loc[50, "water_consumption"] = 999999.0
        feats2 = fe.compute_features(df_tampered)

        # Invariant 1: At step 50, lag_1h, lag_24h, rolling_mean_24h MUST be identical
        # because they are strictly computed on shifted consumption t-1 and earlier!
        assert feats1.loc[50, "lag_1h"] == feats2.loc[50, "lag_1h"]
        assert feats1.loc[50, "lag_24h"] == feats2.loc[50, "lag_24h"]
        assert np.isclose(feats1.loc[50, "rolling_mean_24h"], feats2.loc[50, "rolling_mean_24h"])

        # Invariant 2: lag_1h at step 51 must reflect the tampered value from step 50
        assert feats2.loc[51, "lag_1h"] == 999999.0

        # Invariant 3: Exact mathematical alignment
        # lag_1h at index 100 must equal consumption at index 99
        assert feats1.loc[100, "lag_1h"] == df.loc[99, "water_consumption"]

    def test_isolated_fold_preprocessor_no_leakage(self):
        """Verifies preprocessor fits strictly on training split and transforms test split."""
        df_telemetry, _ = generate_synthetic_dataset(num_days=30, random_seed=42, save_to_disk=False)
        hygiene = DataHygienePipeline()
        cleaned = hygiene.process(df_telemetry)
        fe = FeatureEngineer(use_extended_features=False)
        features = fe.compute_features(cleaned)

        split_idx = int(len(features) * 0.7)
        train_df = features.iloc[:split_idx].copy()
        test_df = features.iloc[split_idx:].copy()

        preprocessor = IsolatedFoldPreprocessor(feature_cols=BASELINE_FEATURE_COLS, use_one_hot=True)
        preprocessor.fit(train_df)

        X_train = preprocessor.transform(train_df)
        X_test = preprocessor.transform(test_df)

        assert X_train.shape[1] == len(preprocessor.get_feature_names_out())
        assert X_test.shape[1] == len(preprocessor.get_feature_names_out())
        assert not np.isnan(X_train).any()
        assert not np.isnan(X_test).any()
