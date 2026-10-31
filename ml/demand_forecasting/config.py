"""AquaMind AI - Demand Forecasting Configuration.

Defines all configuration dataclasses, campus asset parameters,
weather endpoint parameters, and reproducible seeds.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal


@dataclass(frozen=True)
class PathConfig:
    """Directory paths for the demand forecasting module."""
    BASE_DIR: Path = Path(__file__).resolve().parent
    DATA_DIR: Path = BASE_DIR / "data"
    MODELS_DIR: Path = BASE_DIR / "models"
    RUNNER_UPS_DIR: Path = MODELS_DIR / "runner_ups"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    
    # Specific file locations
    SYNTHETIC_DATA_PATH: Path = DATA_DIR / "synthetic_campus_water.csv"
    WEATHER_CACHE_PATH: Path = DATA_DIR / "weather_cache.csv"
    WINNING_PIPELINE_PATH: Path = MODELS_DIR / "winning_pipeline.joblib"
    MODEL_COMPARISON_JSON: Path = OUTPUTS_DIR / "model_comparison.json"
    MODEL_COMPARISON_CSV: Path = OUTPUTS_DIR / "model_comparison.csv"
    METRICS_JSON: Path = OUTPUTS_DIR / "metrics.json"


@dataclass(frozen=True)
class WeatherConfig:
    """Weather API client configuration."""
    LATITUDE: float = 12.9716  # Campus latitude (e.g., IISc / Tech Campus)
    LONGITUDE: float = 77.5946  # Campus longitude
    TIMEZONE: str = "UTC"
    FORECAST_ENDPOINT: str = "https://api.open-meteo.com/v1/forecast"
    ARCHIVE_ENDPOINT: str = "https://archive-api.open-meteo.com/v1/archive"
    TIMEOUT_SECONDS: float = 3.0
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.5


@dataclass(frozen=True)
class CampusBuildingConfig:
    """Building metadata and physical capacity boundaries (L/hour)."""
    # Key: building_id -> (Building Type, Base Hourly Consumption, Peak Design Capacity)
    BUILDINGS: Dict[str, Dict[str, float | str]] = field(default_factory=lambda: {
        "hostel_01": {
            "type": "hostel",
            "base_lph": 1800.0,
            "peak_capacity_lph": 7500.0,
            "occupancy_scale": 1.0,
        },
        "academic_block_01": {
            "type": "academic_block",
            "base_lph": 1200.0,
            "peak_capacity_lph": 6000.0,
            "occupancy_scale": 1.0,
        },
        "library_01": {
            "type": "library",
            "base_lph": 600.0,
            "peak_capacity_lph": 3000.0,
            "occupancy_scale": 0.8,
        },
        "canteen_01": {
            "type": "canteen",
            "base_lph": 1500.0,
            "peak_capacity_lph": 8000.0,
            "occupancy_scale": 1.2,
        },
        "research_lab_01": {
            "type": "research_lab",
            "base_lph": 2200.0,
            "peak_capacity_lph": 9000.0,
            "occupancy_scale": 0.5,
        },
    })


@dataclass(frozen=True)
class ModelTrainingConfig:
    """Hyperparameters and cross-validation protocols."""
    RANDOM_SEED: int = 42
    TRAIN_SPLIT_RATIO: float = 0.70
    VAL_SPLIT_RATIO: float = 0.15
    TEST_SPLIT_RATIO: float = 0.15
    CV_FOLDS: int = 3
    HORIZONS: List[int] = field(default_factory=lambda: [24, 48, 72])
    
    # Feature engineering lag definitions
    LAG_HOURS: List[int] = field(default_factory=lambda: [1, 24, 168])
    ROLLING_HOURS: List[int] = field(default_factory=lambda: [24, 168])  # 24h, 7d
    
    # Missing value threshold
    SHORT_GAP_MAX_HOURS: int = 3
    
    # Target Hackathon Benchmarks
    TARGET_MAPE: float = 6.5
    TARGET_GROUNDEDNESS_PCT: float = 100.0
    TARGET_LATENCY_MAX_SEC: float = 2.0
    TARGET_FALSE_ALARM_MAX_PCT: float = 5.0
    TARGET_TASK_SUCCESS_MIN_PCT: float = 95.0
    
    ACTIVE_MODEL: str = "XGBoostRegressor_Tuned"


PATHS = PathConfig()
WEATHER = WeatherConfig()
BUILDINGS = CampusBuildingConfig()
TRAINING = ModelTrainingConfig()

# Ensure directories exist
PATHS.DATA_DIR.mkdir(parents=True, exist_ok=True)
PATHS.MODELS_DIR.mkdir(parents=True, exist_ok=True)
PATHS.RUNNER_UPS_DIR.mkdir(parents=True, exist_ok=True)
PATHS.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
