"""AquaMind AI - Water Demand Forecasting FastAPI Service Layer.

Exposes REST API endpoints for multi-horizon building water demand forecasting:
1. GET  /api/forecast/health: Pipeline status, versioning, and provider health.
2. GET  /api/forecast/metrics: Evaluated validation leaderboard and audit trail.
3. GET  /api/forecast/{building_id}?horizon=24|48|72: Campus repository forecast.
4. POST /api/forecast/predict: On-demand telemetry forecasting with dynamic rollouts.

Enforces strict static route precedence to prevent /{building_id} capturing /health or /metrics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from ml.demand_forecasting.config import BUILDINGS, PATHS
from ml.demand_forecasting.forecast import get_pipeline, predict
from ml.demand_forecasting.weather_api import WeatherProvider, get_default_weather_provider

# Configurable weather provider hook (facilitates testing & dependency injection)
_OVERRIDE_WEATHER_PROVIDER: Optional[WeatherProvider] = None


def set_weather_provider(provider: Optional[WeatherProvider]) -> None:
    """Sets a custom weather provider (e.g. mock or test fixture)."""
    global _OVERRIDE_WEATHER_PROVIDER
    _OVERRIDE_WEATHER_PROVIDER = provider


def get_active_weather_provider() -> WeatherProvider:
    """Returns active weather provider, favoring override if configured."""
    return _OVERRIDE_WEATHER_PROVIDER or get_default_weather_provider()


# ==============================================================================
# Pydantic v2 Request & Response Schemas
# ==============================================================================


class HealthResponse(BaseModel):
    """Health check and model telemetry status response."""
    status: str = Field(default="healthy", description="Service health indicator")
    model_loaded: bool = Field(..., description="Whether model weights are loaded in memory")
    model_version: str = Field(default="v1.0.0", description="Semver identifier of model artifact")
    selected_model_name: str = Field(..., description="Active production forecaster architecture")
    active_weather_provider: str = Field(..., description="Active weather ingestion service")
    is_synthetic: bool = Field(default=True, description="Flag indicating synthetic training provenance")
    available_buildings: List[str] = Field(..., description="List of recognized campus asset identifiers")


class HistoricalTelemetryItem(BaseModel):
    """Hourly historical observation record."""
    timestamp: str = Field(..., description="ISO-8601 formatted timestamp")
    water_consumption: float = Field(..., ge=0.0, description="Observed water consumption in liters/hour")
    temperature: Optional[float] = Field(default=None, description="Ambient temperature in °C")
    rainfall: Optional[float] = Field(default=None, description="Hourly rainfall in mm")
    occupancy: Optional[float] = Field(default=None, description="Estimated building headcount factor")


class ForecastRequest(BaseModel):
    """Payload for on-demand multi-horizon recursive forecasting."""
    building_id: str = Field(..., description="Target campus building identifier")
    horizon: int = Field(default=24, description="Forecasting horizon (24, 48, or 72 hours)")
    recent_history: Optional[List[HistoricalTelemetryItem]] = Field(
        default=None,
        description="Historical telemetry buffer (minimum 168 hours required if provided)",
    )

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v not in (24, 48, 72):
            raise ValueError(f"Invalid horizon '{v}'. Supported horizons: 24, 48, or 72 hours.")
        return v

    @field_validator("building_id")
    @classmethod
    def validate_building_id(cls, v: str) -> str:
        if v not in BUILDINGS.BUILDINGS:
            raise ValueError(
                f"Unknown building_id '{v}'. Available campus assets: {list(BUILDINGS.BUILDINGS.keys())}"
            )
        return v

    @field_validator("recent_history")
    @classmethod
    def validate_history(
        cls, v: Optional[List[HistoricalTelemetryItem]]
    ) -> Optional[List[HistoricalTelemetryItem]]:
        if v is not None:
            if len(v) < 168:
                raise ValueError(
                    f"Insufficient telemetry history: {len(v)} observations provided, minimum 168 hours (1 week) required."
                )

            # Check timestamp formatting and strict chronological ascending order
            parsed_timestamps = []
            for idx, item in enumerate(v):
                try:
                    ts = pd.to_datetime(item.timestamp)
                except Exception:
                    raise ValueError(f"Invalid ISO-8601 timestamp at index {idx}: '{item.timestamp}'")
                parsed_timestamps.append(ts)

            for i in range(1, len(parsed_timestamps)):
                if parsed_timestamps[i] <= parsed_timestamps[i - 1]:
                    raise ValueError(
                        f"Telemetry history must be in strictly ascending chronological order. "
                        f"Non-ascending sequence detected at index {i} ('{parsed_timestamps[i]}' <= '{parsed_timestamps[i - 1]}')."
                    )

        return v


class HourlyPrediction(BaseModel):
    """Individual hourly forecasted consumption item."""
    timestamp: str = Field(..., description="ISO-8601 prediction timestamp")
    predicted_consumption: float = Field(..., ge=0.0, description="Forecasted water consumption in liters/hour")


class ForecastResponse(BaseModel):
    """Standardized water demand forecasting response."""
    building_id: str = Field(..., description="Campus asset identifier")
    building_type: str = Field(..., description="Asset classification")
    forecast_generated_at: str = Field(..., description="UTC ISO-8601 timestamp of forecast generation")
    horizon_hours: int = Field(..., description="Forecast window length in hours")
    forecast_start_time: str = Field(..., description="Start timestamp of forecast rollout")
    unit: str = Field(default="litres", description="Consumption measurement unit")
    is_synthetic: bool = Field(default=True, description="Flag indicating synthetic training provenance")
    model_name: str = Field(..., description="Production model architecture name")
    model_version: str = Field(default="v1.0.0", description="Model artifact version")
    weather_source: str = Field(..., description="Weather telemetry source ('open-meteo', 'local', 'provided')")
    data_quality: Dict[str, Any] = Field(..., description="Data imputation and quality metadata")
    predictions: List[HourlyPrediction] = Field(..., description="Hourly forecasted demand series")
    total_predicted_consumption: float = Field(..., ge=0.0, description="Cumulative predicted consumption in liters")
    peak_predicted_consumption: float = Field(..., ge=0.0, description="Peak predicted consumption in liters/hour")
    min_predicted_consumption: float = Field(..., ge=0.0, description="Minimum predicted consumption in liters/hour")
    execution_latency_ms: float = Field(..., ge=0.0, description="Model inference runtime in milliseconds")


# ==============================================================================
# Router Definition (Strict Route Precedence Enforced)
# ==============================================================================

router = APIRouter(prefix="/api/forecast", tags=["Water Demand Forecasting"])


# 1. STATIC ROUTE 1: Health Check (Must precede /{building_id})
@router.get("/health", response_model=HealthResponse, summary="Pipeline Health Check")
async def get_forecast_health():
    """Returns model loading state, active architecture, version, and provider status."""
    try:
        pipeline = get_pipeline()
        model_loaded = pipeline is not None and "model" in pipeline
        model_version = pipeline.get("model_version", "v1.0.0") if pipeline else "unknown"
        selected_model_name = pipeline.get("model_name", "CatBoost") if pipeline else "none"
    except Exception as exc:
        model_loaded = False
        model_version = "unknown"
        selected_model_name = "none"

    if not model_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Forecasting pipeline is currently unavailable or failed to initialize.",
        )

    wp = get_active_weather_provider()
    provider_name = type(wp).__name__

    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
        model_version=model_version,
        selected_model_name=selected_model_name,
        active_weather_provider=provider_name,
        is_synthetic=True,
        available_buildings=list(BUILDINGS.BUILDINGS.keys()),
    )


# 2. STATIC ROUTE 2: Metrics Summary (Must precede /{building_id})
@router.get("/metrics", summary="Model Evaluation & Leaderboard Metrics")
async def get_forecast_metrics():
    """Serves the model comparison leaderboard and validation benchmarks."""
    metrics_path = PATHS.OUTPUTS_DIR / "model_comparison.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model comparison metrics file 'model_comparison.json' was not found.",
        )

    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics_data = json.load(f)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read metrics file: {exc}",
        )

    return {
        "status": "success",
        "is_synthetic": True,
        "total_evaluated_models": len(metrics_data) if isinstance(metrics_data, list) else 0,
        "leaderboard": metrics_data,
        "models": metrics_data,
    }


# 3. PARAMETRIZED ROUTE: Building Forecast (Declared AFTER static routes)
@router.get("/{building_id}", response_model=ForecastResponse, summary="Get Forecast by Building ID")
async def get_building_forecast(
    building_id: str,
    horizon: int = Query(default=24, description="Forecasting horizon (24, 48, or 72 hours)"),
):
    """Generates a multi-horizon forecast for a campus building using stored telemetry."""
    if building_id not in BUILDINGS.BUILDINGS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown building_id '{building_id}'. Valid campus assets: {list(BUILDINGS.BUILDINGS.keys())}",
        )

    if horizon not in (24, 48, 72):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid horizon '{horizon}'. Supported horizons: 24, 48, or 72 hours.",
        )

    try:
        pipeline = get_pipeline()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forecasting model pipeline unavailable: {exc}",
        )

    wp = get_active_weather_provider()

    try:
        forecast_dict = predict(
            building_id=building_id,
            horizon=horizon,
            weather_provider=wp,
        )
        return ForecastResponse(**forecast_dict)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error during forecast execution: {exc}",
        )


# 4. ACTION ROUTE: On-Demand Forecast POST
@router.post("/predict", response_model=ForecastResponse, summary="On-Demand Forecast Prediction")
async def post_predict(request: ForecastRequest):
    """Generates an on-demand forecast using caller-supplied telemetry history."""
    try:
        pipeline = get_pipeline()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forecasting model pipeline unavailable: {exc}",
        )

    history_records = None
    if request.recent_history is not None:
        history_records = [item.model_dump() for item in request.recent_history]

    wp = get_active_weather_provider()

    try:
        forecast_dict = predict(
            building_id=request.building_id,
            horizon=request.horizon,
            history=history_records,
            weather_provider=wp,
        )
        return ForecastResponse(**forecast_dict)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error during forecast execution: {exc}",
        )


# ==============================================================================
# Standalone App Instance (Enables Direct Testing & Development)
# ==============================================================================

app = FastAPI(
    title="AquaMind AI - NEERARAN Water Demand Forecasting API",
    description="High-performance, physically grounded hourly water demand forecasting service.",
    version="1.0.0",
)
app.include_router(router)
