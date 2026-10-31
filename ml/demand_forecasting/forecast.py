"""AquaMind AI - In-Memory Water Demand Forecasting Python API.

Provides direct programmatic forecasting interface for downstream autonomous agents:
    forecast.predict(building_id, horizon, history=None, weather=None)
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from ml.demand_forecasting.config import BUILDINGS, PATHS, TRAINING
from ml.demand_forecasting.data_loader import load_telemetry_data
from ml.demand_forecasting.feature_pipeline import (
    DataHygienePipeline,
    FeatureEngineer,
)
from ml.demand_forecasting.multi_horizon_engine import MultiHorizonForecaster
from ml.demand_forecasting.weather_api import WeatherProvider, get_default_weather_provider

# In-memory singleton pipeline cache
_PIPELINE_CACHE: Optional[Dict[str, Any]] = None


def get_pipeline(pipeline_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieves or loads the serialized production pipeline from disk."""
    global _PIPELINE_CACHE
    path = pipeline_path or PATHS.WINNING_PIPELINE_PATH
    if _PIPELINE_CACHE is None or not Path(path).exists():
        if not Path(path).exists():
            from ml.demand_forecasting.train import train_and_export_winning_pipeline
            _PIPELINE_CACHE = train_and_export_winning_pipeline()
        else:
            _PIPELINE_CACHE = joblib.load(path)
    return _PIPELINE_CACHE


def predict(
    building_id: str,
    horizon: int = 72,
    history: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
    weather: Optional[Union[pd.DataFrame, List[Dict[str, Any]]]] = None,
    weather_provider: Optional[WeatherProvider] = None,
) -> Dict[str, Any]:
    """Generates multi-horizon water demand forecasts for a campus building.
    
    Args:
        building_id: Target campus asset identifier (e.g., 'hostel_01', 'academic_block_01').
        horizon: Prediction window in hours (24, 48, or 72).
        history: Optional historical telemetry (DataFrame or list of records). If None, loads repo data.
        weather: Optional future weather forecasts (DataFrame or list of records).
        weather_provider: Optional custom weather provider instance.

    Returns:
        Structured forecast response dictionary with predictions, latency, and data quality metadata.
    """
    t_start = time.perf_counter()
    pipeline = get_pipeline()
    model = pipeline["model"]
    preprocessor = pipeline["preprocessor"]
    fe = pipeline.get("feature_engineer", FeatureEngineer(use_extended_features=True))
    wp = weather_provider or get_default_weather_provider()

    # 1. Prepare Historical Telemetry
    warnings: List[str] = []
    missing_filled = 0

    if history is None:
        raw_hist = load_telemetry_data()
    else:
        raw_hist = pd.DataFrame(history)
        if "building_id" not in raw_hist.columns:
            raw_hist["building_id"] = building_id
        if "building_type" not in raw_hist.columns:
            b_info = BUILDINGS.BUILDINGS.get(building_id, {})
            raw_hist["building_type"] = b_info.get("type", "academic_block")

    raw_hist["timestamp"] = pd.to_datetime(raw_hist["timestamp"])
    b_hist = raw_hist[raw_hist["building_id"] == building_id].sort_values("timestamp").reset_index(drop=True)

    if len(b_hist) < 168:
        raise ValueError(
            f"Insufficient telemetry history for building '{building_id}'. "
            f"Received {len(b_hist)} observations; minimum 168 hours (1 week) required."
        )

    # Apply data hygiene to history
    hygiene = DataHygienePipeline()
    cleaned_hist = hygiene.process(b_hist)
    missing_filled = int(b_hist["water_consumption"].isna().sum()) if "water_consumption" in b_hist.columns else 0

    # 2. Prepare Future Weather
    future_weather_df: Optional[pd.DataFrame] = None
    weather_source = "open-meteo"
    last_known_ts = cleaned_hist["timestamp"].iloc[-1]
    forecast_start_ts = last_known_ts + pd.Timedelta(hours=1)

    if weather is not None:
        future_weather_df = pd.DataFrame(weather)
        future_weather_df["timestamp"] = pd.to_datetime(future_weather_df["timestamp"])
        weather_source = "provided"

    # 3. Execute Recursive Forecast
    engine = MultiHorizonForecaster(
        model=model,
        preprocessor=preprocessor,
        feature_engineer=fe,
        weather_provider=wp,
    )

    pred_df, resolved_weather_source = engine.predict_horizon(
        building_id=building_id,
        historical_df=cleaned_hist,
        horizon_hours=horizon,
        forecast_start_time=forecast_start_ts,
        future_weather_df=future_weather_df,
    )

    total_consumption = round(float(pred_df["predicted_consumption"].sum()), 2)
    peak_consumption = round(float(pred_df["predicted_consumption"].max()), 2)
    min_consumption = round(float(pred_df["predicted_consumption"].min()), 2)
    latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
    b_info = BUILDINGS.BUILDINGS.get(building_id, {})

    return {
        "building_id": building_id,
        "building_type": str(b_info.get("type", "unknown")),
        "forecast_generated_at": datetime.now(timezone.utc).isoformat(),
        "horizon_hours": horizon,
        "forecast_start_time": forecast_start_ts.isoformat(),
        "unit": "litres",
        "is_synthetic": True,
        "model_version": pipeline.get("model_version", "v1.0.0"),
        "model_name": pipeline.get("model_name", "CatBoost"),
        "weather_source": resolved_weather_source if weather is None else weather_source,
        "data_quality": {
            "missing_filled": missing_filled,
            "warnings": warnings,
        },
        "predictions": pred_df.to_dict(orient="records"),
        "total_predicted_consumption": total_consumption,
        "peak_predicted_consumption": peak_consumption,
        "min_predicted_consumption": min_consumption,
        "execution_latency_ms": latency_ms,
    }
