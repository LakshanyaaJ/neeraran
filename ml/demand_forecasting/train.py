"""AquaMind AI - Model Training & Cross-Validation Pipeline.

Executes:
1. Chronological Train / Val / Test splitting (70% / 15% / 15%).
2. Isolated preprocessor fitting strictly on training fold.
3. Out-of-fold prediction generation for StackingMetaEnsemble.
4. Candidate model fitting across baselines, linear, trees, deep, and ensembles.
5. Feature set ablation and global vs per-building model comparisons.
"""

import copy
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
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
from ml.demand_forecasting.config import PATHS, TRAINING
from ml.demand_forecasting.data_loader import load_telemetry_data
from ml.demand_forecasting.feature_pipeline import (
    BASELINE_FEATURE_COLS,
    EXTENDED_FEATURE_COLS,
    DataHygienePipeline,
    FeatureEngineer,
    IsolatedFoldPreprocessor,
)
from ml.demand_forecasting.models_registry import get_all_candidate_factories
from ml.demand_forecasting.tuning import tune_candidate_model

logger = logging.getLogger(__name__)


def split_telemetry_data(
    df: pd.DataFrame,
    train_ratio: float = TRAINING.TRAIN_SPLIT_RATIO,
    val_ratio: float = TRAINING.VAL_SPLIT_RATIO,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Chronologically splits telemetry per building into Train, Val, and Test subsets."""
    train_dfs, val_dfs, test_dfs = [], [], []

    for _, group in df.groupby("building_id"):
        group = group.sort_values("timestamp").reset_index(drop=True)
        n = len(group)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        train_dfs.append(group.iloc[:train_end])
        val_dfs.append(group.iloc[train_end:val_end])
        test_dfs.append(group.iloc[val_end:])

    train_df = pd.concat(train_dfs, ignore_index=True).sort_values(["building_id", "timestamp"]).reset_index(drop=True)
    val_df = pd.concat(val_dfs, ignore_index=True).sort_values(["building_id", "timestamp"]).reset_index(drop=True)
    test_df = pd.concat(test_dfs, ignore_index=True).sort_values(["building_id", "timestamp"]).reset_index(drop=True)

    return train_df, val_df, test_df


def generate_oof_predictions(
    base_models: List[BaseForecaster],
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_splits: int = 3,
) -> np.ndarray:
    """Generates out-of-fold cross-validation predictions matrix to prevent meta-learner leakage."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    n_samples = len(X_train)
    oof_matrix = np.zeros((n_samples, len(base_models)))

    for m_idx, model in enumerate(base_models):
        m_copy = copy.deepcopy(model)
        for tr_idx, val_idx in tscv.split(X_train):
            X_tr, y_tr = X_train[tr_idx], y_train[tr_idx]
            X_val = X_train[val_idx]
            m_copy.fit(X_tr, y_tr)
            oof_matrix[val_idx, m_idx] = m_copy.predict(X_val)

        # For the earliest split where no prior training fold exists, use earliest trained fold
        first_val_idx = list(tscv.split(X_train))[0][1]
        earliest_unseen_end = first_val_idx[0]
        if earliest_unseen_end > 0:
            oof_matrix[:earliest_unseen_end, m_idx] = np.mean(y_train[:earliest_unseen_end])

    return oof_matrix


def train_all_models(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    use_extended_features: bool = True,
    tune_hyperparameters: bool = True,
) -> Dict[str, Any]:
    """Trains full candidate suite, creates ensembles, and returns fitted models + preprocessor."""
    feature_cols = EXTENDED_FEATURE_COLS if use_extended_features else BASELINE_FEATURE_COLS
    
    # Strictly isolated preprocessor fit on train_df
    preprocessor = IsolatedFoldPreprocessor(
        feature_cols=feature_cols,
        use_one_hot=True,
        scale_features=True,
    )
    preprocessor.fit(train_df)

    X_train = preprocessor.transform(train_df)
    y_train = train_df["water_consumption"].values
    X_val = preprocessor.transform(val_df)
    y_val = val_df["water_consumption"].values

    factories = get_all_candidate_factories()
    fitted_models: Dict[str, BaseForecaster] = {}

    # 1. Baselines & Core Models
    for name, factory in factories.items():
        logger.info(f"Fitting candidate model: {name}")
        model = factory()
        if isinstance(model, (SeasonalNaiveForecaster, MovingAverageForecaster)):
            model.fit(train_df, y_train)
        else:
            model.fit(X_train, y_train)
        fitted_models[name] = model

    # 2. Hyperparameter Tuning for XGBoost and LightGBM
    X_train_df = pd.DataFrame(X_train)
    y_train_s = pd.Series(y_train)

    if tune_hyperparameters and HAS_XGBOOST:
        logger.info("Executing TimeSeriesSplit hyperparameter tuning for XGBoost...")
        tuned_xgb, best_p, best_score = tune_candidate_model(
            model_name="XGBoost",
            X_train=X_train_df,
            y_train=y_train_s,
            n_splits=TRAINING.CV_FOLDS,
            n_trials=8,
        )
        tuned_xgb.name = "XGBoost_Tuned"
        fitted_models["XGBoost_Tuned"] = tuned_xgb

    if tune_hyperparameters and HAS_LIGHTGBM:
        logger.info("Executing TimeSeriesSplit hyperparameter tuning for LightGBM...")
        tuned_lgb, best_p, best_score = tune_candidate_model(
            model_name="LightGBM",
            X_train=X_train_df,
            y_train=y_train_s,
            n_splits=TRAINING.CV_FOLDS,
            n_trials=8,
        )
        tuned_lgb.name = "LightGBM_Tuned"
        fitted_models["LightGBM_Tuned"] = tuned_lgb

    # 3. Ensembles
    # Evaluate 1-step validation MAE to pick top 3 base models
    val_scores = {}
    for name, model in fitted_models.items():
        if isinstance(model, (SeasonalNaiveForecaster, MovingAverageForecaster)):
            preds = model.predict(val_df)
        else:
            preds = model.predict(X_val)
        mae = float(np.mean(np.abs(preds - y_val)))
        val_scores[name] = mae

    # Top 3 non-baseline models
    ranked_models = [m for m, _ in sorted(val_scores.items(), key=lambda x: x[1]) if m not in ("SeasonalNaive", "MovingAverage24h")]
    top3_names = ranked_models[:3]
    top3_models = [fitted_models[m] for m in top3_names]
    
    top3_ensemble = Top3AverageEnsemble(models=top3_models, name="Top3AverageEnsemble")
    fitted_models["Top3AverageEnsemble"] = top3_ensemble

    # Stacking meta-ensemble with OOF predictions
    stacking_base_names = top3_names
    stacking_base_models = [copy.deepcopy(fitted_models[m]) for m in stacking_base_names]
    oof_mat = generate_oof_predictions(stacking_base_models, X_train, y_train, n_splits=TRAINING.CV_FOLDS)
    
    stacking_ensemble = StackingMetaEnsemble(base_models=stacking_base_models)
    stacking_ensemble.fit_with_oof(X_train, y_train, oof_predictions=oof_mat)
    fitted_models["StackingMetaEnsemble"] = stacking_ensemble

    return {
        "fitted_models": fitted_models,
        "preprocessor": preprocessor,
        "feature_cols": feature_cols,
        "X_train": X_train,
        "y_train": y_train,
        "X_val": X_val,
        "y_val": y_val,
    }


def train_and_export_winning_pipeline(
    version_tag: str = "v1.0.0",
    active_model_name: str = "CatBoost",
) -> Dict[str, Any]:
    """Retrains the validated winning model on Train+Val splits and exports the winning pipeline.
    
    Exports:
    - winning_pipeline.joblib: fitted pipeline with estimator, preprocessor, feature definitions, dataset hash.
    - runner_ups/: serialized weights for Top3Average, XGBoost, and LightGBM.
    """
    logger.info("Loading telemetry for final production pipeline training...")
    df_raw = load_telemetry_data()
    
    # Calculate dataset SHA-256 hash
    with open(PATHS.SYNTHETIC_DATA_PATH, "rb") as f:
        dataset_hash = hashlib.sha256(f.read()).hexdigest()[:16]

    hygiene = DataHygienePipeline()
    cleaned = hygiene.process(df_raw)

    fe = FeatureEngineer(use_extended_features=True)
    features = fe.compute_features(cleaned)

    # 70% Train, 15% Val, 15% Test
    train_df, val_df, test_df = split_telemetry_data(features)
    train_val_df = pd.concat([train_df, val_df], ignore_index=True).sort_values(["building_id", "timestamp"]).reset_index(drop=True)
    logger.info(f"Combined Train+Val dataset size: {len(train_val_df)} rows. Held-out Test: {len(test_df)} rows.")

    # Fit isolated preprocessor on Train+Val
    preprocessor = IsolatedFoldPreprocessor(
        feature_cols=EXTENDED_FEATURE_COLS,
        use_one_hot=True,
        scale_features=True,
    )
    preprocessor.fit(train_val_df)
    X_train_val = preprocessor.transform(train_val_df)
    y_train_val = train_val_df["water_consumption"].values

    # Train winning model: CatBoost
    logger.info("Fitting winning model: CatBoost...")
    winning_model = CatBoostForecaster(iterations=300, learning_rate=0.06, depth=6, random_seed=TRAINING.RANDOM_SEED)
    winning_model.fit(X_train_val, y_train_val)

    # Train runner-ups: XGBoost, LightGBM, Top3AverageEnsemble
    logger.info("Fitting runner-up models...")
    xgb_runner = XGBoostForecaster(n_estimators=200, learning_rate=0.05, max_depth=6, random_state=TRAINING.RANDOM_SEED)
    xgb_runner.fit(X_train_val, y_train_val)

    lgb_runner = LightGBMForecaster(n_estimators=200, learning_rate=0.05, num_leaves=31, random_state=TRAINING.RANDOM_SEED)
    lgb_runner.fit(X_train_val, y_train_val)

    top3_runner = Top3AverageEnsemble(models=[winning_model, xgb_runner, lgb_runner], name="Top3AverageEnsemble")

    # Serialize runner-ups
    PATHS.RUNNER_UPS_DIR.mkdir(parents=True, exist_ok=True)
    xgb_runner.save(PATHS.RUNNER_UPS_DIR / "XGBoost.joblib")
    lgb_runner.save(PATHS.RUNNER_UPS_DIR / "LightGBM.joblib")
    top3_runner.save(PATHS.RUNNER_UPS_DIR / "Top3AverageEnsemble.joblib")

    # Package winning pipeline
    pipeline_artifact = {
        "model": winning_model,
        "preprocessor": preprocessor,
        "feature_engineer": fe,
        "feature_cols": EXTENDED_FEATURE_COLS,
        "transformed_feature_names": preprocessor.get_feature_names_out(),
        "model_name": winning_model.name,
        "model_version": version_tag,
        "dataset_hash": dataset_hash,
        "dataset_type": "synthetic",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "train_rows": len(train_val_df),
        "test_rows": len(test_df),
        "building_ids": list(train_val_df["building_id"].unique()),
        "runner_up_models": ["XGBoost", "LightGBM", "Top3AverageEnsemble"],
    }

    PATHS.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline_artifact, PATHS.WINNING_PIPELINE_PATH)
    logger.info(f"Winning pipeline successfully exported to: {PATHS.WINNING_PIPELINE_PATH}")

    return pipeline_artifact


if __name__ == "__main__":
    train_and_export_winning_pipeline()
