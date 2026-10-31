"""AquaMind AI - Data Hygiene & Leak-Free Feature Engineering Pipeline.

Enforces:
1. Chronological ordering, duplicate removal, continuous hourly reindexing.
2. Short gap (<= 3h) linear interpolation, long gap (> 3h) non-imputation flagging.
3. Strict shifted computation rule: y_t is never in rolling or lag features of hour t.
4. IsolatedFoldPreprocessor fitting strictly on training slices during CV.
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.demand_forecasting.config import TRAINING

# Baseline feature set
BASELINE_FEATURE_COLS = [
    "hour",
    "day_of_week",
    "month",
    "temperature",
    "rainfall",
    "occupancy",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_mean_24h",
    "rolling_mean_7d",
]

# Extended feature set for ablation
EXTENDED_FEATURE_COLS = BASELINE_FEATURE_COLS + [
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
    "is_holiday",
    "rolling_std_24h",
    "rolling_min_24h",
    "rolling_max_24h",
    "temp_lag_1h",
    "temp_lag_24h",
    "rain_rolling_sum_24h",
]


def clean_and_impute_series(series: pd.Series, max_gap: int = TRAINING.SHORT_GAP_MAX_HOURS) -> Tuple[pd.Series, pd.Series]:
    """Interpolates gaps <= max_gap hours; flags and leaves gaps > max_gap hours untouched.
    
    Returns:
        Tuple of (imputed_series, is_long_gap_series).
    """
    is_na = series.isna()
    if not is_na.any():
        return series.copy(), pd.Series(False, index=series.index)

    # Identify continuous runs of NaNs
    blocks = (~is_na).cumsum()
    gap_sizes = is_na.groupby(blocks).transform("sum")

    # Short gaps (<= max_gap) are interpolated linearly
    short_gap_mask = is_na & (gap_sizes <= max_gap)
    long_gap_mask = is_na & (gap_sizes > max_gap)

    # Perform linear interpolation
    imputed = series.interpolate(method="linear", limit=max_gap, limit_direction="forward")
    # For leading NaNs within short limit
    imputed = imputed.bfill(limit=max_gap)

    # Re-apply NaN to long gaps to ensure they are NOT automatically imputed
    imputed[long_gap_mask] = np.nan

    return imputed, long_gap_mask


class DataHygienePipeline:
    """Preprocesses raw telemetry data enforcing alignment, deduplication, and gap hygiene."""

    def __init__(self, short_gap_max_hours: int = TRAINING.SHORT_GAP_MAX_HOURS):
        self.short_gap_max_hours = short_gap_max_hours

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans, sorts, deduplicates, and reindexes hourly continuous time series."""
        df_clean = df.copy()
        df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"])
        if df_clean["timestamp"].dt.tz is not None:
            df_clean["timestamp"] = df_clean["timestamp"].dt.tz_convert(None)

        # Drop duplicates by (building_id, timestamp)
        df_clean = df_clean.drop_duplicates(subset=["building_id", "timestamp"], keep="last")

        cleaned_dfs = []
        for building_id, group in df_clean.groupby("building_id"):
            group = group.sort_values("timestamp")
            
            # Reindex to continuous hourly series
            min_ts = group["timestamp"].min()
            max_ts = group["timestamp"].max()
            full_index = pd.date_range(start=min_ts, end=max_ts, freq="h", name="timestamp")
            
            group_reindexed = group.set_index("timestamp").reindex(full_index)
            group_reindexed["building_id"] = building_id
            if "building_type" in group.columns:
                group_reindexed["building_type"] = group["building_type"].iloc[0]

            # Weather & occupancy forward/backward fill for minor missing timestamps
            for col in ["temperature", "rainfall", "occupancy"]:
                if col in group_reindexed.columns:
                    group_reindexed[col] = group_reindexed[col].ffill().bfill()

            # Time columns derived directly from timestamp
            group_reindexed["hour"] = group_reindexed.index.hour
            group_reindexed["day_of_week"] = group_reindexed.index.dayofweek
            group_reindexed["month"] = group_reindexed.index.month
            group_reindexed["is_weekend"] = group_reindexed["day_of_week"].isin([5, 6]).astype(int)

            if "is_holiday" not in group_reindexed.columns or group_reindexed["is_holiday"].isna().all():
                is_vacation = (group_reindexed["month"] == 6)
                group_reindexed["is_holiday"] = (group_reindexed["is_weekend"] == 1) | is_vacation
            group_reindexed["is_holiday"] = group_reindexed["is_holiday"].astype(int)

            # Impute short gaps in water_consumption; flag long gaps
            if "water_consumption" in group_reindexed.columns:
                imputed_cons, is_long_gap = clean_and_impute_series(
                    group_reindexed["water_consumption"],
                    max_gap=self.short_gap_max_hours,
                )
                group_reindexed["water_consumption"] = imputed_cons
                group_reindexed["is_long_gap"] = is_long_gap
            else:
                group_reindexed["is_long_gap"] = False

            if "is_synthetic" not in group_reindexed.columns:
                group_reindexed["is_synthetic"] = group.get("is_synthetic", pd.Series(True)).iloc[0]

            cleaned_dfs.append(group_reindexed.reset_index())

        result = pd.concat(cleaned_dfs, ignore_index=True)
        return result.sort_values(["building_id", "timestamp"]).reset_index(drop=True)


class FeatureEngineer:
    """Computes leak-free lag, rolling, and cyclical features with shifted computation."""

    def __init__(self, use_extended_features: bool = True):
        self.use_extended_features = use_extended_features

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generates all features per building group obeying the shifted computation rule."""
        df_feat = df.copy()
        output_dfs = []

        for _, group in df_feat.groupby("building_id"):
            group = group.sort_values("timestamp").copy()
            cons = group["water_consumption"]

            # CRITICAL LEAKAGE PREVENTION: Shift consumption by 1 before any lag or rolling calculation
            shifted_cons = cons.shift(1)

            # Mandatory Lags
            group["lag_1h"] = shifted_cons  # Equivalent to cons.shift(1)
            group["lag_24h"] = cons.shift(24)
            group["lag_168h"] = cons.shift(168)

            # Mandatory Rolling Statistics (strictly on shifted data)
            group["rolling_mean_24h"] = shifted_cons.rolling(window=24, min_periods=1).mean()
            group["rolling_mean_7d"] = shifted_cons.rolling(window=168, min_periods=1).mean()

            # Extended Features for ablation
            if self.use_extended_features:
                # Cyclical time encodings
                group["hour_sin"] = np.sin(2 * np.pi * group["hour"] / 24.0)
                group["hour_cos"] = np.cos(2 * np.pi * group["hour"] / 24.0)
                group["dow_sin"] = np.sin(2 * np.pi * group["day_of_week"] / 7.0)
                group["dow_cos"] = np.cos(2 * np.pi * group["day_of_week"] / 7.0)
                group["month_sin"] = np.sin(2 * np.pi * (group["month"] - 1) / 12.0)
                group["month_cos"] = np.cos(2 * np.pi * (group["month"] - 1) / 12.0)

                # Rolling dispersion
                group["rolling_std_24h"] = shifted_cons.rolling(window=24, min_periods=1).std().fillna(0.0)
                group["rolling_min_24h"] = shifted_cons.rolling(window=24, min_periods=1).min()
                group["rolling_max_24h"] = shifted_cons.rolling(window=24, min_periods=1).max()

                # Exogenous weather lags
                group["temp_lag_1h"] = group["temperature"].shift(1).bfill()
                group["temp_lag_24h"] = group["temperature"].shift(24).bfill()
                group["rain_rolling_sum_24h"] = group["rainfall"].shift(1).rolling(24, min_periods=1).sum().fillna(0.0)

            output_dfs.append(group)

        result = pd.concat(output_dfs, ignore_index=True)
        return result.sort_values(["building_id", "timestamp"]).reset_index(drop=True)


class IsolatedFoldPreprocessor(BaseEstimator, TransformerMixin):
    """Leak-free preprocessor fit strictly on training fold slices during CV.
    
    Scales numerical features, imputes warm-up lags using training statistics,
    and encodes categorical building IDs.
    """

    def __init__(
        self,
        feature_cols: Optional[List[str]] = None,
        use_one_hot: bool = True,
        scale_features: bool = True,
    ):
        self.feature_cols = feature_cols or BASELINE_FEATURE_COLS
        self.use_one_hot = use_one_hot
        self.scale_features = scale_features
        self.encoder: Optional[OneHotEncoder] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_medians: Dict[str, float] = {}
        self.transformed_feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        """Fits scaler, categorical encoder, and training-fold medians strictly on X."""
        X_df = X.copy()
        
        # Calculate training fold medians for warm-up lag imputation
        for col in self.feature_cols:
            if col in X_df.columns:
                self.feature_medians[col] = float(X_df[col].median(skipna=True))

        # Setup OneHotEncoder for building_id
        if self.use_one_hot and "building_id" in X_df.columns:
            self.encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            self.encoder.fit(X_df[["building_id"]])
            enc_names = [f"building_{cat}" for cat in self.encoder.categories_[0]]
        else:
            self.encoder = None
            enc_names = []

        # Impute missing features with fitted medians before scaler fit
        X_num = self._impute_numerical(X_df)
        
        if self.scale_features:
            self.scaler = StandardScaler()
            self.scaler.fit(X_num)
        else:
            self.scaler = None

        self.transformed_feature_names = list(self.feature_cols) + enc_names
        return self

    def _impute_numerical(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fills missing lags with training-fold medians without looking at future rows."""
        X_num = X[self.feature_cols].copy()
        for col in self.feature_cols:
            median_val = self.feature_medians.get(col, 0.0)
            X_num[col] = X_num[col].fillna(median_val)
        return X_num

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Transforms input DataFrame using strictly fitted parameters."""
        X_df = X.copy()
        X_num = self._impute_numerical(X_df)
        
        if self.scaler is not None:
            num_arr = self.scaler.transform(X_num)
        else:
            num_arr = X_num.values

        if self.encoder is not None and "building_id" in X_df.columns:
            cat_arr = self.encoder.transform(X_df[["building_id"]])
            return np.hstack([num_arr, cat_arr])

        return num_arr

    def get_feature_names_out(self) -> List[str]:
        return self.transformed_feature_names
