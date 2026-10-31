"""AquaMind AI - Candidate Model Wrappers & Ensemble Implementations.

Defines a unified BaseForecaster interface supporting:
1. Baselines: Seasonal Naive (t-168) and Moving Average (24h).
2. Regularized Linear: Ridge and ElasticNet.
3. Tree Ensembles: RandomForest, ExtraTrees, XGBoost, LightGBM, CatBoost, HistGradientBoosting.
4. Soft Deep / Specialized: PyTorch MLP and Prophet with graceful fallback.
5. Ensembles: Top-3 Average and StackingMetaEnsemble (Ridge meta-learner trained on OOF predictions).
"""

import abc
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)

logger = logging.getLogger(__name__)

# Soft imports
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("xgboost not installed; XGBoostForecaster will be unavailable.")

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    logger.warning("lightgbm not installed; LightGBMForecaster will be unavailable.")

try:
    import catboost as cb
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False
    logger.warning("catboost not installed; CatBoostForecaster will be unavailable.")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("torch not installed; PyTorchMLPForecaster will be unavailable.")

try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False
    logger.info("prophet not installed; skipping Prophet candidate gracefully.")


class BaseForecaster(abc.ABC):
    """Unified interface for all water demand forecasting candidate models."""

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}
        self.is_fitted = False
        self.feature_names: Optional[List[str]] = None

    @abc.abstractmethod
    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "BaseForecaster":
        """Fits the model to training data."""
        pass

    @abc.abstractmethod
    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Generates demand predictions, strictly clipped at 0 (non-negative)."""
        pass

    def get_params(self) -> Dict[str, Any]:
        """Returns model hyperparameters."""
        return self.params.copy()

    def save(self, filepath: Union[str, Path]) -> None:
        """Serializes forecaster state to disk via joblib."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "BaseForecaster":
        """Loads serialized forecaster from disk."""
        return joblib.load(Path(filepath))

    def _prepare_inputs(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Optional[Union[np.ndarray, pd.Series]] = None,
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Converts DataFrames or array-likes to clean float64 numpy arrays."""
        if isinstance(X, pd.DataFrame):
            non_numeric = [c for c in ["timestamp", "building_id", "building_type", "is_synthetic"] if c in X.columns]
            X_clean = X.drop(columns=non_numeric, errors="ignore")
            X_clean = X_clean.select_dtypes(include=[np.number, bool])
            if self.feature_names is None:
                self.feature_names = list(X_clean.columns)
            X_arr = X_clean.values.astype(np.float64)
        else:
            X_arr = np.asarray(X, dtype=np.float64)

        # Replace any residual NaNs with column medians or 0.0
        if np.isnan(X_arr).any():
            col_medians = np.nanmedian(X_arr, axis=0)
            col_medians = np.nan_to_num(col_medians, nan=0.0)
            nan_indices = np.where(np.isnan(X_arr))
            X_arr[nan_indices] = np.take(col_medians, nan_indices[1])

        y_arr = None
        if y is not None:
            if isinstance(y, (pd.Series, pd.DataFrame)):
                y_arr = y.values.ravel().astype(np.float64)
            else:
                y_arr = np.asarray(y, dtype=np.float64).ravel()

        return X_arr, y_arr


# ==============================================================================
# 1. Baseline Models
# ==============================================================================

class SeasonalNaiveForecaster(BaseForecaster):
    """Predicts water consumption as the exact observation from 1 week ago (t-168)."""

    def __init__(self, lag_168_col_idx: int = 8):
        super().__init__(name="SeasonalNaive", params={"lag_168_col_idx": lag_168_col_idx})
        self.lag_col_idx = lag_168_col_idx
        self.fallback_mean = 1000.0

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "SeasonalNaiveForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        if isinstance(X, pd.DataFrame) and "lag_168h" in X.columns:
            self.lag_col_idx = X.columns.get_loc("lag_168h")
        self.fallback_mean = float(np.nanmean(y_arr)) if y_arr is not None else 1000.0
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if isinstance(X, pd.DataFrame) and "lag_168h" in X.columns:
            vals = X["lag_168h"].values.astype(np.float64)
        else:
            X_arr, _ = self._prepare_inputs(X)
            if self.lag_col_idx < X_arr.shape[1]:
                vals = X_arr[:, self.lag_col_idx]
            else:
                vals = np.full(X_arr.shape[0], self.fallback_mean)

        vals = np.nan_to_num(vals, nan=self.fallback_mean)
        return np.maximum(0.0, vals)


class MovingAverageForecaster(BaseForecaster):
    """Predicts water consumption as the rolling 24-hour shifted mean."""

    def __init__(self, rolling_mean_24h_col_idx: int = 9):
        super().__init__(name="MovingAverage24h", params={"rolling_mean_24h_col_idx": rolling_mean_24h_col_idx})
        self.ma_col_idx = rolling_mean_24h_col_idx
        self.fallback_mean = 1000.0

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "MovingAverageForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        if isinstance(X, pd.DataFrame) and "rolling_mean_24h" in X.columns:
            self.ma_col_idx = X.columns.get_loc("rolling_mean_24h")
        self.fallback_mean = float(np.nanmean(y_arr)) if y_arr is not None else 1000.0
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if isinstance(X, pd.DataFrame) and "rolling_mean_24h" in X.columns:
            vals = X["rolling_mean_24h"].values.astype(np.float64)
        else:
            X_arr, _ = self._prepare_inputs(X)
            if self.ma_col_idx < X_arr.shape[1]:
                vals = X_arr[:, self.ma_col_idx]
            else:
                vals = np.full(X_arr.shape[0], self.fallback_mean)

        vals = np.nan_to_num(vals, nan=self.fallback_mean)
        return np.maximum(0.0, vals)


# ==============================================================================
# 2. Regularized Linear Models
# ==============================================================================

class RidgeForecaster(BaseForecaster):
    """L2 Regularized Linear Regression forecaster."""

    def __init__(self, alpha: float = 1.0, random_state: int = 42):
        super().__init__(name="Ridge", params={"alpha": alpha, "random_state": random_state})
        self.model = Ridge(alpha=alpha, random_state=random_state)

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "RidgeForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class ElasticNetForecaster(BaseForecaster):
    """ElasticNet Regularized Regression (L1 + L2 penalty) forecaster."""

    def __init__(self, alpha: float = 0.5, l1_ratio: float = 0.5, random_state: int = 42):
        super().__init__(name="ElasticNet", params={"alpha": alpha, "l1_ratio": l1_ratio, "random_state": random_state})
        self.model = ElasticNet(alpha=alpha, l1_ratio=l1_ratio, random_state=random_state, max_iter=2000)

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "ElasticNetForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


# ==============================================================================
# 3. Tree Ensemble Models
# ==============================================================================

class RandomForestForecaster(BaseForecaster):
    """Random Forest Ensemble forecaster."""

    def __init__(self, n_estimators: int = 80, max_depth: Optional[int] = 12, random_state: int = 42):
        super().__init__(name="RandomForest", params={"n_estimators": n_estimators, "max_depth": max_depth, "random_state": random_state})
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=1,
        )

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "RandomForestForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class ExtraTreesForecaster(BaseForecaster):
    """Extremely Randomized Trees forecaster."""

    def __init__(self, n_estimators: int = 80, max_depth: Optional[int] = 12, random_state: int = 42):
        super().__init__(name="ExtraTrees", params={"n_estimators": n_estimators, "max_depth": max_depth, "random_state": random_state})
        self.model = ExtraTreesRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=1,
        )

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "ExtraTreesForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class HistGradientBoostingForecaster(BaseForecaster):
    """Scikit-Learn Histogram-based Gradient Boosting forecaster."""

    def __init__(self, max_iter: int = 150, learning_rate: float = 0.08, max_depth: Optional[int] = 8, random_state: int = 42):
        super().__init__(name="HistGradientBoosting", params={"max_iter": max_iter, "learning_rate": learning_rate, "max_depth": max_depth, "random_state": random_state})
        self.model = HistGradientBoostingRegressor(
            max_iter=max_iter,
            learning_rate=learning_rate,
            max_depth=max_depth,
            random_state=random_state,
        )

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "HistGradientBoostingForecaster":
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class XGBoostForecaster(BaseForecaster):
    """XGBoost Regressor forecaster."""

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42,
    ):
        params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "random_state": random_state,
        }
        super().__init__(name="XGBoost", params=params)
        if HAS_XGBOOST:
            self.model = xgb.XGBRegressor(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                subsample=subsample,
                colsample_bytree=colsample_bytree,
                reg_alpha=reg_alpha,
                reg_lambda=reg_lambda,
                random_state=random_state,
                objective="reg:squarederror",
                n_jobs=-1,
            )
        else:
            self.model = None

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "XGBoostForecaster":
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost is not installed.")
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if not HAS_XGBOOST:
            raise RuntimeError("XGBoost is not installed.")
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class LightGBMForecaster(BaseForecaster):
    """LightGBM Regressor forecaster."""

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        max_depth: int = 7,
        num_leaves: int = 31,
        subsample: float = 0.85,
        random_state: int = 42,
    ):
        params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "subsample": subsample,
            "random_state": random_state,
        }
        super().__init__(name="LightGBM", params=params)
        if HAS_LIGHTGBM:
            self.model = lgb.LGBMRegressor(
                n_estimators=n_estimators,
                learning_rate=learning_rate,
                max_depth=max_depth,
                num_leaves=num_leaves,
                subsample=subsample,
                random_state=random_state,
                verbosity=-1,
                n_jobs=-1,
            )
        else:
            self.model = None

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "LightGBMForecaster":
        if not HAS_LIGHTGBM:
            raise RuntimeError("LightGBM is not installed.")
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if not HAS_LIGHTGBM:
            raise RuntimeError("LightGBM is not installed.")
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


class CatBoostForecaster(BaseForecaster):
    """CatBoost Regressor forecaster."""

    def __init__(
        self,
        iterations: int = 250,
        learning_rate: float = 0.06,
        depth: int = 6,
        random_seed: int = 42,
    ):
        params = {
            "iterations": iterations,
            "learning_rate": learning_rate,
            "depth": depth,
            "random_seed": random_seed,
        }
        super().__init__(name="CatBoost", params=params)
        if HAS_CATBOOST:
            self.model = cb.CatBoostRegressor(
                iterations=iterations,
                learning_rate=learning_rate,
                depth=depth,
                random_seed=random_seed,
                verbose=0,
                thread_count=-1,
            )
        else:
            self.model = None

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "CatBoostForecaster":
        if not HAS_CATBOOST:
            raise RuntimeError("CatBoost is not installed.")
        X_arr, y_arr = self._prepare_inputs(X, y)
        self.model.fit(X_arr, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if not HAS_CATBOOST:
            raise RuntimeError("CatBoost is not installed.")
        X_arr, _ = self._prepare_inputs(X)
        preds = self.model.predict(X_arr)
        return np.maximum(0.0, preds)


# ==============================================================================
# 4. Soft Deep Learning: PyTorch MLP
# ==============================================================================

if HAS_TORCH:
    class _MLPNet(nn.Module):
        def __init__(self, in_features: int, hidden_dim: int = 64):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_features, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1),
            )

        def forward(self, x):
            return self.net(x)


class PyTorchMLPForecaster(BaseForecaster):
    """Lightweight PyTorch MLP forecaster for soft deep learning exploration."""

    def __init__(self, hidden_dim: int = 64, epochs: int = 25, lr: float = 0.005, random_state: int = 42):
        super().__init__(name="PyTorchMLP", params={"hidden_dim": hidden_dim, "epochs": epochs, "lr": lr})
        self.hidden_dim = hidden_dim
        self.epochs = epochs
        self.lr = lr
        self.random_state = random_state
        self.net = None

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "PyTorchMLPForecaster":
        if not HAS_TORCH:
            raise RuntimeError("PyTorch is not installed.")
        torch.manual_seed(self.random_state)
        X_arr, y_arr = self._prepare_inputs(X, y)

        in_dim = X_arr.shape[1]
        self.net = _MLPNet(in_features=in_dim, hidden_dim=self.hidden_dim)
        optimizer = optim.Adam(self.net.parameters(), lr=self.lr)
        criterion = nn.MSELoss()

        X_t = torch.tensor(X_arr, dtype=torch.float32)
        y_t = torch.tensor(y_arr, dtype=torch.float32).unsqueeze(1)

        self.net.train()
        batch_size = 256
        n_samples = len(X_arr)

        for _ in range(self.epochs):
            permutation = torch.randperm(n_samples)
            for i in range(0, n_samples, batch_size):
                indices = permutation[i : i + batch_size]
                batch_x, batch_y = X_t[indices], y_t[indices]
                optimizer.zero_grad()
                outputs = self.net(batch_x)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        if not HAS_TORCH or self.net is None:
            raise RuntimeError("PyTorch MLP is not fitted or PyTorch is absent.")
        X_arr, _ = self._prepare_inputs(X)
        self.net.eval()
        with torch.no_grad():
            preds = self.net(torch.tensor(X_arr, dtype=torch.float32)).numpy().ravel()
        return np.maximum(0.0, preds)


# ==============================================================================
# 5. Ensemble Models
# ==============================================================================

class Top3AverageEnsemble(BaseForecaster):
    """Combines top 3 validated model predictions via simple arithmetic average."""

    def __init__(self, models: List[BaseForecaster], name: str = "Top3AverageEnsemble"):
        super().__init__(name=name, params={"model_names": [m.name for m in models]})
        self.models = models

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "Top3AverageEnsemble":
        for model in self.models:
            model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        preds = [model.predict(X) for model in self.models]
        avg_preds = np.mean(preds, axis=0)
        return np.maximum(0.0, avg_preds)


class StackingMetaEnsemble(BaseForecaster):
    """Stacking ensemble using a non-negative Ridge meta-learner on base model predictions."""

    def __init__(self, base_models: List[BaseForecaster], meta_learner: Optional[Any] = None):
        super().__init__(name="StackingMetaEnsemble", params={"base_models": [m.name for m in base_models]})
        self.base_models = base_models
        self.meta_learner = meta_learner or Ridge(alpha=1.0, positive=True, random_state=42)

    def fit_with_oof(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series],
        oof_predictions: np.ndarray,
    ) -> "StackingMetaEnsemble":
        """Fits meta-learner strictly on out-of-fold CV predictions to prevent leakage."""
        _, y_arr = self._prepare_inputs(X, y)
        # Fit base models on full training data
        for model in self.base_models:
            model.fit(X, y)
        # Fit meta-learner on out-of-fold matrix
        self.meta_learner.fit(oof_predictions, y_arr)
        self.is_fitted = True
        return self

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Union[np.ndarray, pd.Series]) -> "StackingMetaEnsemble":
        # Direct fallback fit if explicit OOF matrix is not provided
        X_arr, y_arr = self._prepare_inputs(X, y)
        base_preds = []
        for model in self.base_models:
            model.fit(X, y)
            base_preds.append(model.predict(X))
        meta_features = np.column_stack(base_preds)
        self.meta_learner.fit(meta_features, y_arr)
        self.is_fitted = True
        return self

    def predict(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        base_preds = [model.predict(X) for model in self.base_models]
        meta_features = np.column_stack(base_preds)
        preds = self.meta_learner.predict(meta_features)
        return np.maximum(0.0, preds)
