"""AquaMind AI - Hyperparameter Tuning Engine.

Provides expanding-window TimeSeriesSplit hyperparameter optimization
for tree ensembles and regularized models.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from ml.demand_forecasting.candidate_models import (
    BaseForecaster,
    CatBoostForecaster,
    LightGBMForecaster,
    RidgeForecaster,
    XGBoostForecaster,
    HAS_CATBOOST,
    HAS_LIGHTGBM,
    HAS_XGBOOST,
)

logger = logging.getLogger(__name__)

PARAM_DISTRIBUTIONS: Dict[str, Dict[str, List[Any]]] = {
    "XGBoost": {
        "n_estimators": [120, 180, 240],
        "learning_rate": [0.03, 0.05, 0.08],
        "max_depth": [4, 6, 8],
        "subsample": [0.75, 0.85, 0.95],
        "reg_alpha": [0.01, 0.1, 1.0],
        "reg_lambda": [0.5, 1.0, 3.0],
    },
    "LightGBM": {
        "n_estimators": [120, 180, 240],
        "learning_rate": [0.03, 0.05, 0.08],
        "num_leaves": [15, 31, 63],
        "max_depth": [5, 7, 9],
        "subsample": [0.75, 0.85, 0.95],
    },
    "CatBoost": {
        "iterations": [150, 220, 300],
        "learning_rate": [0.03, 0.06, 0.1],
        "depth": [4, 6, 8],
    },
    "Ridge": {
        "alpha": [0.01, 0.1, 1.0, 10.0, 50.0],
    },
}


def sample_hyperparameters(param_grid: Dict[str, List[Any]], rng: np.random.RandomState) -> Dict[str, Any]:
    """Randomly samples a configuration from a discrete grid with native types."""
    return {k: v[int(rng.choice(len(v)))] for k, v in param_grid.items()}


def tune_candidate_model(
    model_name: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    n_splits: int = 3,
    n_trials: int = 15,
    random_seed: int = 42,
) -> Tuple[BaseForecaster, Dict[str, Any], float]:
    """Tunes a model using expanding-window TimeSeriesSplit cross-validation on train folds.
    
    Returns:
        Tuple of (best_fitted_forecaster, best_params_dict, best_mean_cv_mae).
    """
    rng = np.random.RandomState(random_seed)
    grid = PARAM_DISTRIBUTIONS.get(model_name, {})
    if not grid:
        raise ValueError(f"No tuning grid defined for model '{model_name}'.")

    tscv = TimeSeriesSplit(n_splits=n_splits)
    best_mae = float("inf")
    best_params: Dict[str, Any] = {}

    for trial in range(n_trials):
        params = sample_hyperparameters(grid, rng)
        fold_maes: List[float] = []

        for train_idx, val_idx in tscv.split(X_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            # Instantiate forecaster with trial parameters
            if model_name == "XGBoost" and HAS_XGBOOST:
                model = XGBoostForecaster(**params, random_state=random_seed)
            elif model_name == "LightGBM" and HAS_LIGHTGBM:
                model = LightGBMForecaster(**params, random_state=random_seed)
            elif model_name == "CatBoost" and HAS_CATBOOST:
                model = CatBoostForecaster(**params, random_seed=random_seed)
            elif model_name == "Ridge":
                model = RidgeForecaster(**params, random_state=random_seed)
            else:
                continue

            model.fit(X_tr, y_tr)
            preds = model.predict(X_val)
            mae = float(np.mean(np.abs(preds - y_val.values)))
            fold_maes.append(mae)

        mean_mae = float(np.mean(fold_maes))
        if mean_mae < best_mae:
            best_mae = mean_mae
            best_params = params.copy()

    # Re-train best model on full training fold
    if model_name == "XGBoost" and HAS_XGBOOST:
        best_model = XGBoostForecaster(**best_params, random_state=random_seed)
    elif model_name == "LightGBM" and HAS_LIGHTGBM:
        best_model = LightGBMForecaster(**best_params, random_state=random_seed)
    elif model_name == "CatBoost" and HAS_CATBOOST:
        best_model = CatBoostForecaster(**best_params, random_seed=random_seed)
    elif model_name == "Ridge":
        best_model = RidgeForecaster(**best_params, random_state=random_seed)
    else:
        raise RuntimeError(f"Cannot instantiate best model for '{model_name}'.")

    best_model.fit(X_train, y_train)
    best_model.name = f"{model_name}_Tuned"
    return best_model, best_params, best_mae
