"""Unit Tests for Phase B & B2 - Candidate Model Wrappers, CV Isolation & Selection.

Verifies:
1. BaseForecaster uniform contract (fit, predict, get_params, save, load).
2. Non-negative predictions bounding (zero negative consumption).
3. Expanding-window TimeSeriesSplit temporal ordering (no future leakage).
4. Soft dependency fallback resilience.
5. Statistical significance calculations (Diebold-Mariano & Bootstrap CI).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import TimeSeriesSplit

from ml.demand_forecasting.candidate_models import (
    BaseForecaster,
    CatBoostForecaster,
    ElasticNetForecaster,
    ExtraTreesForecaster,
    HistGradientBoostingForecaster,
    LightGBMForecaster,
    MovingAverageForecaster,
    PyTorchMLPForecaster,
    RandomForestForecaster,
    RidgeForecaster,
    SeasonalNaiveForecaster,
    StackingMetaEnsemble,
    Top3AverageEnsemble,
    XGBoostForecaster,
    HAS_CATBOOST,
    HAS_LIGHTGBM,
    HAS_TORCH,
    HAS_XGBOOST,
)
from ml.demand_forecasting.compare_models import (
    compute_bootstrap_ci,
    compute_diebold_mariano,
    compute_metrics,
)
from ml.demand_forecasting.models_registry import create_candidate_model, get_all_candidate_factories


@pytest.fixture
def synthetic_toy_data():
    """Generates small reproducible tabular features and target."""
    rng = np.random.RandomState(42)
    n = 200
    X = rng.normal(size=(n, 10))
    # Simulated consumption: positive values with trend and noise
    y = np.maximum(50.0, 1500.0 + 30.0 * X[:, 0] + 50.0 * X[:, 1] + rng.normal(0, 20, size=n))
    return X, y


class TestBaseForecasterContract:
    """Verifies that all candidate models adhere strictly to BaseForecaster interface."""

    @pytest.mark.parametrize("model_class,kwargs", [
        (SeasonalNaiveForecaster, {}),
        (MovingAverageForecaster, {}),
        (RidgeForecaster, {"alpha": 1.0}),
        (ElasticNetForecaster, {"alpha": 0.1}),
        (RandomForestForecaster, {"n_estimators": 10, "max_depth": 5}),
        (ExtraTreesForecaster, {"n_estimators": 10, "max_depth": 5}),
        (HistGradientBoostingForecaster, {"max_iter": 20}),
    ])
    def test_core_model_lifecycle(self, model_class, kwargs, synthetic_toy_data, tmp_path):
        X, y = synthetic_toy_data
        model = model_class(**kwargs)
        
        # 1. Fit
        model.fit(X, y)
        assert model.is_fitted

        # 2. Predict & Non-negative bounding
        preds = model.predict(X)
        assert isinstance(preds, np.ndarray)
        assert len(preds) == len(y)
        assert (preds >= 0.0).all(), "Predictions must never be negative"

        # 3. Hyperparameters
        params = model.get_params()
        assert isinstance(params, dict)

        # 4. Serialization & Loading
        save_file = tmp_path / f"{model.name}_test.joblib"
        model.save(save_file)
        assert save_file.exists()

        loaded_model = BaseForecaster.load(save_file)
        loaded_preds = loaded_model.predict(X)
        np.testing.assert_allclose(preds, loaded_preds)

    def test_xgboost_forecaster_lifecycle(self, synthetic_toy_data):
        if not HAS_XGBOOST:
            pytest.skip("xgboost not installed")
        X, y = synthetic_toy_data
        model = XGBoostForecaster(n_estimators=15, max_depth=3)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)
        assert (preds >= 0.0).all()

    def test_lightgbm_forecaster_lifecycle(self, synthetic_toy_data):
        if not HAS_LIGHTGBM:
            pytest.skip("lightgbm not installed")
        X, y = synthetic_toy_data
        model = LightGBMForecaster(n_estimators=15, max_depth=3)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)
        assert (preds >= 0.0).all()

    def test_catboost_forecaster_lifecycle(self, synthetic_toy_data):
        if not HAS_CATBOOST:
            pytest.skip("catboost not installed")
        X, y = synthetic_toy_data
        model = CatBoostForecaster(iterations=15, depth=3)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)
        assert (preds >= 0.0).all()

    def test_pytorch_mlp_lifecycle(self, synthetic_toy_data):
        if not HAS_TORCH:
            pytest.skip("torch not installed")
        X, y = synthetic_toy_data
        model = PyTorchMLPForecaster(hidden_dim=16, epochs=5)
        model.fit(X, y)
        preds = model.predict(X)
        assert len(preds) == len(y)
        assert (preds >= 0.0).all()


class TestEnsembleImplementations:
    """Validates Top3AverageEnsemble and StackingMetaEnsemble."""

    def test_top3_average_ensemble(self, synthetic_toy_data):
        X, y = synthetic_toy_data
        m1 = RidgeForecaster(alpha=1.0)
        m2 = ElasticNetForecaster(alpha=0.1)
        m3 = HistGradientBoostingForecaster(max_iter=10)

        ensemble = Top3AverageEnsemble([m1, m2, m3])
        ensemble.fit(X, y)
        preds = ensemble.predict(X)

        assert len(preds) == len(y)
        assert (preds >= 0.0).all()

        # Check that ensemble equals mean of individual predictions
        expected_mean = (m1.predict(X) + m2.predict(X) + m3.predict(X)) / 3.0
        np.testing.assert_allclose(preds, expected_mean, rtol=1e-5)

    def test_stacking_meta_ensemble(self, synthetic_toy_data):
        X, y = synthetic_toy_data
        m1 = RidgeForecaster(alpha=1.0)
        m2 = HistGradientBoostingForecaster(max_iter=10)

        stack = StackingMetaEnsemble(base_models=[m1, m2])
        stack.fit(X, y)
        preds = stack.predict(X)

        assert len(preds) == len(y)
        assert (preds >= 0.0).all()


class TestValidationIsolationAndSignificance:
    """Verifies expanding-window CV time ordering and metric calculation."""

    def test_expanding_window_temporal_isolation(self):
        n = 100
        tscv = TimeSeriesSplit(n_splits=3)
        indices = np.arange(n)

        for train_idx, val_idx in tscv.split(indices):
            # Strict ordering: every train index must strictly precede all val indices
            assert max(train_idx) < min(val_idx)

    def test_diebold_mariano_and_bootstrap_ci(self):
        rng = np.random.RandomState(42)
        n = 100
        baseline_err = rng.normal(loc=100.0, scale=15.0, size=n)
        candidate_err = rng.normal(loc=70.0, scale=10.0, size=n)  # Clear improvement

        dm_stat, p_val = compute_diebold_mariano(baseline_err, candidate_err)
        ci_low, ci_high = compute_bootstrap_ci(baseline_err, candidate_err)

        assert dm_stat > 0.0, "DM stat should indicate improvement"
        assert p_val < 0.05, "Improvement should be statistically significant"
        assert ci_low > 0.0 and ci_high > ci_low

    def test_metrics_computation(self):
        y_true = np.array([100.0, 200.0, 300.0, 0.05])  # 0.05 should be masked out of MAPE
        y_pred = np.array([105.0, 190.0, 310.0, 0.08])

        metrics = compute_metrics(y_true, y_pred)
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "mape" in metrics
        assert "wape" in metrics
        assert metrics["pct_excluded"] == 25.0  # 1 out of 4 excluded
