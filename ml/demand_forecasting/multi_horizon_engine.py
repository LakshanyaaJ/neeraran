"""AquaMind AI - Multi-Horizon Recursive Forecasting Engine.

Executes recursive multi-step rollouts for 24h, 48h, and 72h horizons.
Implements:
1. Dynamic predictions buffer updating lag_1h, lag_24h, and rolling_mean_24h.
2. Historical anchoring for lag_168h and rolling_mean_7d.
3. Schedule-based future occupancy derivation (zero future leakage).
4. Physical bounding: non-negative and capped at 3x peak design capacity.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ml.demand_forecasting.candidate_models import (
    BaseForecaster,
    MovingAverageForecaster,
    SeasonalNaiveForecaster,
)
from ml.demand_forecasting.config import BUILDINGS, TRAINING
from ml.demand_forecasting.data_loader import get_occupancy_pattern
from ml.demand_forecasting.feature_pipeline import (
    BASELINE_FEATURE_COLS,
    EXTENDED_FEATURE_COLS,
    FeatureEngineer,
    IsolatedFoldPreprocessor,
)
from ml.demand_forecasting.weather_api import WeatherProvider, get_default_weather_provider


class MultiHorizonForecaster:
    """Recursively rolls out hourly forecasts across multi-step windows."""

    def __init__(
        self,
        model: BaseForecaster,
        preprocessor: IsolatedFoldPreprocessor,
        feature_engineer: Optional[FeatureEngineer] = None,
        weather_provider: Optional[WeatherProvider] = None,
    ):
        self.model = model
        self.preprocessor = preprocessor
        self.feature_engineer = feature_engineer or FeatureEngineer(use_extended_features=True)
        self.weather_provider = weather_provider or get_default_weather_provider()

    def predict_horizon(
        self,
        building_id: str,
        historical_df: pd.DataFrame,
        horizon_hours: int = 72,
        forecast_start_time: Optional[datetime] = None,
        future_weather_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, str]:
        """Performs multi-step recursive forecasting for a given building.
        
        Args:
            building_id: Target campus asset identifier.
            historical_df: Historical telemetry for building (at least 168 hours).
            horizon_hours: Forecasting window (24, 48, or 72).
            forecast_start_time: Start timestamp for the forecast window.
            future_weather_df: Optional pre-fetched weather forecast.

        Returns:
            Tuple of (DataFrame with [timestamp, predicted_consumption], weather_source string).
        """
        hist = historical_df[historical_df["building_id"] == building_id].sort_values("timestamp").copy()
        if len(hist) < 168:
            raise ValueError(f"Insufficient historical data: {len(hist)} rows found, minimum 168 hours required.")

        last_known_ts = pd.to_datetime(hist["timestamp"].iloc[-1])
        start_ts = pd.to_datetime(forecast_start_time) if forecast_start_time else last_known_ts + pd.Timedelta(hours=1)
        
        # Ingest future weather
        weather_source = "provided"
        if future_weather_df is None:
            future_weather_df, weather_source = self.weather_provider.get_forecast(
                hours=horizon_hours, start_time=start_ts
            )

        # Retrieve building metadata for physical capacity bounding
        b_info = BUILDINGS.BUILDINGS.get(building_id, {
            "type": "hostel",
            "base_lph": 1500.0,
            "peak_capacity_lph": 7500.0,
        })
        b_type = str(b_info["type"])
        max_physical_cap = float(b_info["peak_capacity_lph"]) * 3.0

        # Maintain dynamic consumption series buffer (history + rollouts)
        cons_buffer = list(hist["water_consumption"].values)
        ts_buffer = list(pd.to_datetime(hist["timestamp"]))

        predictions: List[Dict[str, Any]] = []

        for step in range(horizon_hours):
            current_ts = start_ts + pd.Timedelta(hours=step)
            hour = current_ts.hour
            dow = current_ts.dayofweek
            month = current_ts.month
            
            # Future occupancy derived strictly from schedule lookup rules
            is_vacation = (month == 5 and current_ts.day >= 15) or (month == 6)
            is_weekend = dow in (5, 6)
            is_holiday = int(is_vacation or is_weekend)
            occ = get_occupancy_pattern(b_type, hour, dow, is_vacation)

            # Match weather for this step
            w_row = future_weather_df[pd.to_datetime(future_weather_df["timestamp"]) == current_ts]
            if not w_row.empty:
                temp = float(w_row["temperature"].iloc[0])
                rain = float(w_row["rainfall"].iloc[0])
            else:
                temp = float(future_weather_df["temperature"].iloc[min(step, len(future_weather_df) - 1)])
                rain = float(future_weather_df["rainfall"].iloc[min(step, len(future_weather_df) - 1)])

            # Recursive Lag Updates:
            # lag_1h: most recent element in buffer (t-1)
            lag_1h = cons_buffer[-1]
            # lag_24h: 24 steps back
            lag_24h = cons_buffer[-24] if len(cons_buffer) >= 24 else cons_buffer[0]
            # lag_168h: 168 steps back (from historical telemetry)
            lag_168h = cons_buffer[-168] if len(cons_buffer) >= 168 else cons_buffer[0]

            # Shifted Rolling aggregations on buffer (t-1 and older)
            recent_24 = cons_buffer[-24:]
            rolling_mean_24h = float(np.mean(recent_24))
            recent_168 = cons_buffer[-168:]
            rolling_mean_7d = float(np.mean(recent_168))

            row_data = {
                "timestamp": current_ts,
                "building_id": building_id,
                "building_type": b_type,
                "hour": hour,
                "day_of_week": dow,
                "month": month,
                "temperature": temp,
                "rainfall": rain,
                "occupancy": occ,
                "lag_1h": lag_1h,
                "lag_24h": lag_24h,
                "lag_168h": lag_168h,
                "rolling_mean_24h": rolling_mean_24h,
                "rolling_mean_7d": rolling_mean_7d,
                "is_weekend": int(is_weekend),
                "is_holiday": is_holiday,
            }

            if self.feature_engineer.use_extended_features:
                row_data["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
                row_data["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
                row_data["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
                row_data["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
                row_data["month_sin"] = np.sin(2 * np.pi * (month - 1) / 12.0)
                row_data["month_cos"] = np.cos(2 * np.pi * (month - 1) / 12.0)
                row_data["rolling_std_24h"] = float(np.std(recent_24)) if len(recent_24) > 1 else 0.0
                row_data["rolling_min_24h"] = float(np.min(recent_24))
                row_data["rolling_max_24h"] = float(np.max(recent_24))
                row_data["temp_lag_1h"] = temp
                row_data["temp_lag_24h"] = temp
                row_data["rain_rolling_sum_24h"] = rain

            step_df = pd.DataFrame([row_data])
            if isinstance(self.model, (SeasonalNaiveForecaster, MovingAverageForecaster)):
                y_pred = float(self.model.predict(step_df)[0])
            else:
                X_proc = self.preprocessor.transform(step_df)
                y_pred = float(self.model.predict(X_proc)[0])

            # Grounded physical bounding: non-negative and <= 3x peak physical capacity
            y_pred = max(0.0, min(max_physical_cap, y_pred))

            # Append prediction to buffer for subsequent recursive steps
            cons_buffer.append(y_pred)
            ts_buffer.append(current_ts)

            predictions.append({
                "timestamp": current_ts.isoformat(),
                "predicted_consumption": round(y_pred, 2),
            })

        return pd.DataFrame(predictions), weather_source
