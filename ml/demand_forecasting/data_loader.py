"""AquaMind AI - Synthetic Campus Water Telemetry & Data Ingestion.

Generates realistic, physically-grounded hourly water consumption telemetry
for 5 campus building archetypes across a continuous 6-month period (4,392 hours).
Includes ambient weather correlation, diurnal occupancy patterns, calendar seasonality,
and controlled missingness.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ml.demand_forecasting.config import BUILDINGS, PATHS, TRAINING


def get_occupancy_pattern(building_type: str, hour: int, day_of_week: int, is_vacation: bool) -> float:
    """Computes realistic occupancy load factor [0.0 - 1.0] by building type and calendar."""
    is_weekend = day_of_week in (5, 6)
    
    if building_type == "hostel":
        # Peaks in morning (6:00 - 9:00) and evening/night (18:00 - 23:00)
        if 6 <= hour <= 9:
            base = 0.85 + 0.10 * math.sin((hour - 6) / 3 * math.pi)
        elif 18 <= hour <= 23:
            base = 0.90 + 0.08 * math.sin((hour - 18) / 5 * math.pi)
        elif 10 <= hour <= 17:
            base = 0.35 if not is_weekend else 0.70
        else:
            base = 0.50
        if is_vacation:
            base *= 0.40

    elif building_type == "academic_block":
        # Working hours 8:00 - 17:00 on weekdays; minimal on weekends
        if is_weekend:
            base = 0.05
        else:
            if 8 <= hour <= 17:
                base = 0.80 + 0.15 * math.sin((hour - 8) / 9 * math.pi)
            else:
                base = 0.05
        if is_vacation:
            base *= 0.20

    elif building_type == "library":
        # 9:00 - 22:00, higher during exam terms, moderate on weekends
        if 9 <= hour <= 21:
            base = 0.75 + 0.15 * math.sin((hour - 9) / 12 * math.pi)
            if is_weekend:
                base *= 0.70
        else:
            base = 0.05
        if is_vacation:
            base *= 0.25

    elif building_type == "canteen":
        # Distinct meal spikes: Breakfast (7-9), Lunch (12-14), Dinner (19-21)
        if 7 <= hour <= 9:
            base = 0.75 + 0.15 * math.sin((hour - 7) / 2 * math.pi)
        elif 12 <= hour <= 14:
            base = 0.95 + 0.05 * math.sin((hour - 12) / 2 * math.pi)
        elif 19 <= hour <= 21:
            base = 0.85 + 0.10 * math.sin((hour - 19) / 2 * math.pi)
        elif 15 <= hour <= 18:
            base = 0.30
        else:
            base = 0.05
        if is_weekend:
            base *= 0.75
        if is_vacation:
            base *= 0.35

    elif building_type == "research_lab":
        # Basal 24/7 load with moderate daytime boost (9:00 - 18:00)
        base = 0.45
        if 9 <= hour <= 18:
            base += 0.40 if not is_weekend else 0.15
        if is_vacation:
            base *= 0.75
    else:
        base = 0.50

    return max(0.02, min(1.0, float(base)))


def generate_synthetic_weather(timestamps: pd.DatetimeIndex, random_state: np.random.RandomState) -> pd.DataFrame:
    """Generates continuous hourly synthetic ambient temperature and rainfall series."""
    n = len(timestamps)
    day_of_year = timestamps.dayofyear.values
    hour = timestamps.hour.values
    
    # Base temperature seasonality (warm tropical/subtropical campus climate)
    # Annual cycle: peak in May/June (approx day 130-160), coolest in Jan
    annual_temp = 24.0 + 6.0 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    
    # Diurnal cycle: min at 05:00, peak at 14:00
    diurnal_temp = 5.0 * np.sin(2 * np.pi * (hour - 8) / 24)
    
    temp_noise = random_state.normal(0, 1.2, size=n)
    temperature = annual_temp + diurnal_temp + temp_noise
    
    # Rainfall: occasional convective rain events during monsoon / pre-monsoon
    # Probability increases in late spring / summer (May/June)
    rain_prob = 0.04 + 0.08 * (day_of_year > 120).astype(float)
    rain_events = random_state.uniform(0, 1, size=n) < rain_prob
    rainfall = np.zeros(n, dtype=float)
    rainfall[rain_events] = random_state.gamma(shape=2.0, scale=4.0, size=np.sum(rain_events))
    rainfall = np.round(rainfall, 1)

    return pd.DataFrame({
        "timestamp": timestamps,
        "temperature": np.round(temperature, 1),
        "rainfall": rainfall,
    })


def generate_synthetic_dataset(
    start_date: str = "2026-01-01 00:00:00",
    num_days: int = 183,
    random_seed: int = TRAINING.RANDOM_SEED,
    missing_rate: float = 0.015,
    save_to_disk: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generates a reproducible 6-month hourly water consumption dataset across 5 buildings.
    
    Returns:
        (df_telemetry, df_weather): Tuple of pandas DataFrames.
    """
    rng = np.random.RandomState(random_seed)
    start_dt = pd.to_datetime(start_date)
    timestamps = pd.date_range(start=start_dt, periods=num_days * 24, freq="h")
    
    # Generate unified weather series
    df_weather = generate_synthetic_weather(timestamps, rng)
    
    records: List[Dict] = []
    
    for building_id, b_info in BUILDINGS.BUILDINGS.items():
        b_type = str(b_info["type"])
        base_lph = float(b_info["base_lph"])
        peak_cap = float(b_info["peak_capacity_lph"])
        
        for i, ts in enumerate(timestamps):
            hour = ts.hour
            dow = ts.dayofweek
            month = ts.month
            
            # Academic vacation indicator (e.g., Summer vacation: May 15 to June 30)
            is_vacation = (month == 5 and ts.day >= 15) or (month == 6)
            is_weekend = dow in (5, 6)
            is_holiday = is_vacation or is_weekend
            
            # Occupancy load factor
            occ = get_occupancy_pattern(b_type, hour, dow, is_vacation)
            
            # Weather effects
            temp = df_weather.iloc[i]["temperature"]
            rain = df_weather.iloc[i]["rainfall"]
            
            # Temperature multiplier: higher temp increases cooling/drinking demand
            temp_effect = 1.0 + 0.018 * max(0.0, temp - 22.0)
            
            # Rainfall effect: reduces external washing / landscaping demand
            rain_effect = max(0.85, 1.0 - 0.025 * rain)
            
            # Diurnal noise
            noise = rng.normal(1.0, 0.04)
            
            # Consumption synthesis (strictly physically bounded)
            consumption = (base_lph * (0.35 + 0.65 * occ)) * temp_effect * rain_effect * noise
            
            # Ensure physical capacity envelope
            consumption = max(50.0, min(peak_cap * 0.95, consumption))
            
            records.append({
                "timestamp": ts.isoformat(),
                "building_id": building_id,
                "building_type": b_type,
                "water_consumption": round(float(consumption), 2),
                "temperature": float(temp),
                "rainfall": float(rain),
                "occupancy": round(float(occ), 3),
                "hour": hour,
                "day_of_week": dow,
                "month": month,
                "is_weekend": int(is_weekend),
                "is_holiday": int(is_holiday),
                "is_synthetic": True,
            })
            
    df_telemetry = pd.DataFrame(records)
    
    # Inject 1-2% missing values (MCAR) into water_consumption to test hygiene imputation
    n_rows = len(df_telemetry)
    n_missing = int(n_rows * missing_rate)
    missing_indices = rng.choice(n_rows, size=n_missing, replace=False)
    df_telemetry.loc[missing_indices, "water_consumption"] = np.nan
    
    if save_to_disk:
        PATHS.SYNTHETIC_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_telemetry.to_csv(PATHS.SYNTHETIC_DATA_PATH, index=False)
        
        # Save weather cache for offline WeatherProvider fallback
        PATHS.WEATHER_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_weather.to_csv(PATHS.WEATHER_CACHE_PATH, index=False)
        
    return df_telemetry, df_weather


def load_telemetry_data(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Loads campus water consumption telemetry; falls back to synthetic generation if missing."""
    target_path = PATHS.SYNTHETIC_DATA_PATH if csv_path is None else Path(csv_path)
    
    if not target_path.exists():
        df_telemetry, _ = generate_synthetic_dataset(save_to_disk=True)
        return df_telemetry
        
    df = pd.read_csv(target_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


if __name__ == "__main__":
    print(f"Generating synthetic dataset with seed {TRAINING.RANDOM_SEED}...")
    df_data, df_w = generate_synthetic_dataset()
    print(f"Generated {len(df_data)} records across {df_data['building_id'].nunique()} buildings.")
    print(f"Missing consumption count: {df_data['water_consumption'].isna().sum()} ({df_data['water_consumption'].isna().mean():.2%})")
    print(f"Telemetry saved to: {PATHS.SYNTHETIC_DATA_PATH}")
    print(f"Weather cache saved to: {PATHS.WEATHER_CACHE_PATH}")
