"""AquaMind AI - Candidate Model Registry.

Provides registry lookup and factory instantiation for all baseline,
linear, tree-based, deep learning, and ensemble models.
"""

from typing import Any, Callable, Dict, List

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


def get_all_candidate_factories() -> Dict[str, Callable[[], BaseForecaster]]:
    """Returns factory functions for all available candidate forecasters."""
    factories: Dict[str, Callable[[], BaseForecaster]] = {
        "SeasonalNaive": lambda: SeasonalNaiveForecaster(),
        "MovingAverage24h": lambda: MovingAverageForecaster(),
        "Ridge": lambda: RidgeForecaster(alpha=1.0),
        "ElasticNet": lambda: ElasticNetForecaster(alpha=0.1, l1_ratio=0.5),
        "RandomForest": lambda: RandomForestForecaster(n_estimators=80, max_depth=12),
        "ExtraTrees": lambda: ExtraTreesForecaster(n_estimators=80, max_depth=12),
        "HistGradientBoosting": lambda: HistGradientBoostingForecaster(max_iter=150, learning_rate=0.08),
    }

    if HAS_XGBOOST:
        factories["XGBoost"] = lambda: XGBoostForecaster(n_estimators=180, learning_rate=0.05, max_depth=6)

    if HAS_LIGHTGBM:
        factories["LightGBM"] = lambda: LightGBMForecaster(n_estimators=180, learning_rate=0.05, num_leaves=31)

    if HAS_CATBOOST:
        factories["CatBoost"] = lambda: CatBoostForecaster(iterations=200, learning_rate=0.06, depth=6)

    if HAS_TORCH:
        factories["PyTorchMLP"] = lambda: PyTorchMLPForecaster(hidden_dim=64, epochs=20, lr=0.005)

    return factories


def create_candidate_model(name: str, **kwargs: Any) -> BaseForecaster:
    """Instantiates a candidate model by name with optional parameter overrides."""
    factories = get_all_candidate_factories()
    if name not in factories:
        raise ValueError(f"Unknown or unavailable model name: '{name}'. Available: {list(factories.keys())}")
    model = factories[name]()
    if kwargs:
        model.params.update(kwargs)
    return model
