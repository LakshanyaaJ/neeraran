"""AquaMind AI - Multi-Model Evaluation & Validation Leaderboard Generation.

Executes:
1. Multi-horizon recursive rollout evaluations (24h, 48h, 72h) across all candidate models.
2. Inference latency and training compute tracking.
3. Statistical significance testing: Diebold-Mariano test & Bootstrap 95% CI vs Seasonal Naive.
4. Feature set ablation (Baseline vs Extended) and Architecture comparison (Global vs Per-Building).
5. Exports outputs/model_comparison.json and outputs/model_comparison.csv.
"""

import json
import logging
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from ml.demand_forecasting.candidate_models import (
    BaseForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster,
    XGBoostForecaster,
)
from ml.demand_forecasting.config import BUILDINGS, PATHS, TRAINING
from ml.demand_forecasting.data_loader import load_telemetry_data
from ml.demand_forecasting.feature_pipeline import (
    BASELINE_FEATURE_COLS,
    EXTENDED_FEATURE_COLS,
    DataHygienePipeline,
    FeatureEngineer,
    IsolatedFoldPreprocessor,
)
from ml.demand_forecasting.multi_horizon_engine import MultiHorizonForecaster
from ml.demand_forecasting.train import split_telemetry_data, train_all_models

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes MAE, RMSE, WAPE, and MAPE (masking actuals < 0.1 L/h)."""
    mask = y_true >= 0.1
    y_t = y_true[mask]
    y_p = y_pred[mask]
    pct_excluded = float((~mask).mean() * 100.0)

    mae = float(np.mean(np.abs(y_t - y_p)))
    rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))
    wape = float(np.sum(np.abs(y_t - y_p)) / (np.sum(y_t) + 1e-8) * 100.0)
    mape = float(np.mean(np.abs((y_t - y_p) / (y_t + 1e-8))) * 100.0)
    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    r2 = float(1.0 - (ss_res / (ss_tot + 1e-8)))

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "wape": round(wape, 2),
        "mape": round(mape, 2),
        "r2": round(r2, 4),
        "pct_excluded": round(pct_excluded, 2),
    }


def compute_diebold_mariano(baseline_errors: np.ndarray, candidate_errors: np.ndarray) -> Tuple[float, float]:
    """Computes Diebold-Mariano test statistic and p-value for forecast accuracy differences."""
    d = np.abs(baseline_errors) - np.abs(candidate_errors)
    n = len(d)
    if n < 5:
        return 0.0, 1.0
    mean_d = np.mean(d)
    var_d = np.var(d, ddof=1) / n
    if var_d <= 1e-12:
        return 0.0, 1.0
    dm_stat = float(mean_d / np.sqrt(var_d))
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(dm_stat))))
    return round(dm_stat, 3), round(p_val, 5)


def compute_bootstrap_ci(baseline_errors: np.ndarray, candidate_errors: np.ndarray, n_boot: int = 1000) -> Tuple[float, float]:
    """Computes 95% bootstrap confidence interval for mean absolute error improvement."""
    diff = np.abs(baseline_errors) - np.abs(candidate_errors)
    rng = np.random.RandomState(42)
    boot_means = [np.mean(rng.choice(diff, size=len(diff), replace=True)) for _ in range(n_boot)]
    ci_low = float(np.percentile(boot_means, 2.5))
    ci_high = float(np.percentile(boot_means, 97.5))
    return round(ci_low, 2), round(ci_high, 2)


def evaluate_model_multi_horizon(
    model: BaseForecaster,
    preprocessor: IsolatedFoldPreprocessor,
    val_df: pd.DataFrame,
    horizons: List[int] = [24, 48, 72],
    num_origins: int = 2,
) -> Dict[str, Any]:
    """Evaluates recursive multi-horizon forecast across multiple origins and buildings."""
    engine = MultiHorizonForecaster(model=model, preprocessor=preprocessor)
    buildings = val_df["building_id"].unique()

    horizon_results: Dict[int, Dict[str, List[float]]] = {h: {"actuals": [], "preds": []} for h in horizons}
    latencies: List[float] = []

    for b_id in buildings:
        b_data = val_df[val_df["building_id"] == b_id].sort_values("timestamp").reset_index(drop=True)
        n = len(b_data)
        # Ensure sufficient history (>= 168h) plus horizon evaluation window
        max_h = max(horizons)
        if n < 168 + max_h:
            continue

        step_spacing = max(1, (n - 168 - max_h) // num_origins)
        origins = [168 + i * step_spacing for i in range(num_origins)]

        for origin_idx in origins:
            hist_slice = b_data.iloc[:origin_idx]
            start_ts = b_data["timestamp"].iloc[origin_idx]
            future_weather = b_data.iloc[origin_idx : origin_idx + max_h][["timestamp", "temperature", "rainfall"]].reset_index(drop=True)

            t0 = time.perf_counter()
            pred_df, _ = engine.predict_horizon(
                building_id=b_id,
                historical_df=hist_slice,
                horizon_hours=max_h,
                forecast_start_time=start_ts,
                future_weather_df=future_weather,
            )
            latencies.append((time.perf_counter() - t0) * 1000.0)

            for h in horizons:
                actual_slice = b_data["water_consumption"].iloc[origin_idx : origin_idx + h].values
                pred_slice = pred_df["predicted_consumption"].iloc[:h].values
                min_len = min(len(actual_slice), len(pred_slice))
                horizon_results[h]["actuals"].extend(actual_slice[:min_len])
                horizon_results[h]["preds"].extend(pred_slice[:min_len])

    summary: Dict[str, Any] = {"mean_latency_ms": round(float(np.mean(latencies)), 2) if latencies else 0.0}
    for h in horizons:
        y_t = np.array(horizon_results[h]["actuals"])
        y_p = np.array(horizon_results[h]["preds"])
        m = compute_metrics(y_t, y_p)
        summary[f"{h}h"] = m
        summary[f"{h}h_errors"] = np.abs(y_t - y_p)

    return summary


def run_candidate_comparison() -> pd.DataFrame:
    """Executes full multi-model comparison across baselines, models, and feature sets."""
    logger.info("Loading telemetry dataset...")
    df_raw = load_telemetry_data()

    logger.info("Applying Data Hygiene and Feature Pipeline...")
    hygiene = DataHygienePipeline()
    cleaned = hygiene.process(df_raw)

    fe_extended = FeatureEngineer(use_extended_features=True)
    features_extended = fe_extended.compute_features(cleaned)

    # Chronological Split: 70% Train, 15% Val, 15% Test
    train_df, val_df, test_df = split_telemetry_data(features_extended)
    logger.info(f"Split sizes: Train={len(train_df)}, Val={len(val_df)}, Test={len(test_df)}")

    # Train candidates
    logger.info("Training candidate models...")
    train_artifacts = train_all_models(train_df, val_df, use_extended_features=True, tune_hyperparameters=True)
    fitted_models = train_artifacts["fitted_models"]
    preprocessor = train_artifacts["preprocessor"]

    logger.info("Running Multi-Horizon Recursive Evaluation on Validation Set...")
    results: List[Dict[str, Any]] = []
    baseline_72h_errors: Optional[np.ndarray] = None

    # Collect evaluations
    eval_summaries: Dict[str, Dict[str, Any]] = {}
    for name, model in fitted_models.items():
        logger.info(f"Evaluating {name} across 24h, 48h, 72h horizons...")
        eval_summary = evaluate_model_multi_horizon(model, preprocessor, val_df, horizons=[24, 48, 72])
        eval_summaries[name] = eval_summary

    baseline_72h_errors = eval_summaries.get("SeasonalNaive", {}).get("72h_errors", None)

    for name, eval_summary in eval_summaries.items():
        m24 = eval_summary["24h"]
        m48 = eval_summary["48h"]
        m72 = eval_summary["72h"]
        curr_72h_err = eval_summary["72h_errors"]

        # Statistical significance vs baseline
        if baseline_72h_errors is not None and len(baseline_72h_errors) == len(curr_72h_err) and name != "SeasonalNaive":
            dm_stat, p_val = compute_diebold_mariano(baseline_72h_errors, curr_72h_err)
            ci_low, ci_high = compute_bootstrap_ci(baseline_72h_errors, curr_72h_err)
            improvement_pct = round(
                (float(np.mean(baseline_72h_errors)) - float(np.mean(curr_72h_err)))
                / (float(np.mean(baseline_72h_errors)) + 1e-8)
                * 100.0,
                2,
            )
        else:
            dm_stat, p_val = 0.0, 1.0
            ci_low, ci_high = 0.0, 0.0
            improvement_pct = 0.0

        results.append({
            "model_name": name,
            "mae_24h": m24["mae"],
            "mape_24h": m24["mape"],
            "rmse_24h": m24["rmse"],
            "mae_48h": m48["mae"],
            "mape_48h": m48["mape"],
            "rmse_48h": m48["rmse"],
            "mae_72h": m72["mae"],
            "mape_72h": m72["mape"],
            "rmse_72h": m72["rmse"],
            "r2_72h": m72["r2"],
            "improvement_over_baseline_pct": improvement_pct,
            "diebold_mariano_stat": dm_stat,
            "p_value": p_val,
            "bootstrap_ci_95": f"[{ci_low}, {ci_high}]",
            "inference_latency_ms": eval_summary["mean_latency_ms"],
        })

    # Run Feature Set Ablation Experiment (Baseline vs Extended)
    logger.info("Running Feature Set Ablation experiment on XGBoost...")
    fe_baseline = FeatureEngineer(use_extended_features=False)
    features_base = fe_baseline.compute_features(cleaned)
    tr_b, val_b, _ = split_telemetry_data(features_base)
    prep_b = IsolatedFoldPreprocessor(feature_cols=BASELINE_FEATURE_COLS, use_one_hot=True).fit(tr_b)
    xgb_base = XGBoostForecaster(n_estimators=180, learning_rate=0.05, max_depth=6)
    xgb_base.fit(prep_b.transform(tr_b), tr_b["water_consumption"].values)
    eval_base = evaluate_model_multi_horizon(xgb_base, prep_b, val_b, horizons=[24, 72])

    ablation_df = pd.DataFrame([
        {
            "feature_set": "Baseline (Lags + Rollings + Exogenous)",
            "num_features": len(BASELINE_FEATURE_COLS),
            "mae_24h": eval_base["24h"]["mae"],
            "mape_24h": eval_base["24h"]["mape"],
            "mae_72h": eval_base["72h"]["mae"],
            "mape_72h": eval_base["72h"]["mape"],
        },
        {
            "feature_set": "Extended (Cyclical + Dispersion + Temp/Rain Lags)",
            "num_features": len(EXTENDED_FEATURE_COLS),
            "mae_24h": eval_summaries["XGBoost"]["24h"]["mae"],
            "mape_24h": eval_summaries["XGBoost"]["24h"]["mape"],
            "mae_72h": eval_summaries["XGBoost"]["72h"]["mae"],
            "mape_72h": eval_summaries["XGBoost"]["72h"]["mape"],
        },
    ])
    ablation_df.to_csv(PATHS.OUTPUTS_DIR / "ablation_feature_sets.csv", index=False)

    # Run Architecture Comparison (Unified Global vs Per-Building Isolated)
    logger.info("Running Architecture Comparison (Global vs Per-Building)...")
    buildings = val_df["building_id"].unique()
    per_building_maes_72h = []
    per_building_mapes_72h = []
    for b_id in buildings:
        tr_b_iso = train_df[train_df["building_id"] == b_id].copy()
        val_b_iso = val_df[val_df["building_id"] == b_id].copy()
        prep_iso = IsolatedFoldPreprocessor(feature_cols=EXTENDED_FEATURE_COLS, use_one_hot=False).fit(tr_b_iso)
        xgb_iso = XGBoostForecaster(n_estimators=100, learning_rate=0.06, max_depth=5)
        xgb_iso.fit(prep_iso.transform(tr_b_iso), tr_b_iso["water_consumption"].values)
        eval_iso = evaluate_model_multi_horizon(xgb_iso, prep_iso, val_b_iso, horizons=[72])
        per_building_maes_72h.append(eval_iso["72h"]["mae"])
        per_building_mapes_72h.append(eval_iso["72h"]["mape"])

    arch_df = pd.DataFrame([
        {
            "architecture": "Unified Global Model (One-Hot Encoded building_id)",
            "mae_72h": eval_summaries["XGBoost"]["72h"]["mae"],
            "mape_72h": eval_summaries["XGBoost"]["72h"]["mape"],
        },
        {
            "architecture": "Per-Building Isolated Models (Average across 5 models)",
            "mae_72h": round(float(np.mean(per_building_maes_72h)), 2),
            "mape_72h": round(float(np.mean(per_building_mapes_72h)), 2),
        },
    ])
    arch_df.to_csv(PATHS.OUTPUTS_DIR / "architecture_comparison.csv", index=False)

    leaderboard_df = pd.DataFrame(results).sort_values("mape_72h").reset_index(drop=True)
    leaderboard_df["rank"] = range(1, len(leaderboard_df) + 1)

    # Save to outputs
    PATHS.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    leaderboard_df.to_csv(PATHS.MODEL_COMPARISON_CSV, index=False)
    
    with open(PATHS.MODEL_COMPARISON_JSON, "w", encoding="utf-8") as f:
        json.dump(leaderboard_df.to_dict(orient="records"), f, indent=2)

    return leaderboard_df, ablation_df, arch_df


if __name__ == "__main__":
    df_leaderboard, df_ablation, df_arch = run_candidate_comparison()
    print("\n" + "=" * 95)
    print("                AQUAMIND AI - CANDIDATE MODEL VALIDATION LEADERBOARD")
    print("=" * 95)
    cols_to_print = [
        "rank", "model_name", "mae_24h", "mape_24h", "mae_72h", "mape_72h",
        "improvement_over_baseline_pct", "p_value", "inference_latency_ms"
    ]
    print(df_leaderboard[cols_to_print].to_string(index=False))
    print("=" * 95)

    print("\n" + "=" * 95)
    print("                         FEATURE SET ABLATION EXPERIMENT")
    print("=" * 95)
    print(df_ablation.to_string(index=False))
    print("=" * 95)

    print("\n" + "=" * 95)
    print("                        MODEL ARCHITECTURE COMPARISON")
    print("=" * 95)
    print(df_arch.to_string(index=False))
    print("=" * 95)
