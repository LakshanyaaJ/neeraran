"""
AquaGuard AI - Preprocessing and Feature Engineering Pipelines
Strictly avoids target leakage, fits transformers only on training partitions.
"""

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, RobustScaler
from sklearn.impute import SimpleImputer
import pandas as pd
import numpy as np

def build_abnormal_preprocessor(scaler_type='standard'):
    """
    Build scikit-learn preprocessor pipeline for abnormal consumption.
    Categorical: zone_type
    Numeric: all candidate numerical features
    """
    categorical_cols = ['zone_type']
    numeric_cols = [
        'hour', 'day_of_week', 'is_weekend', 'is_holiday',
        'occupancy', 'scheduled_activity', 'temperature_c',
        'interval_consumption_liters', 'previous_1h_avg_liters',
        'previous_24h_avg_liters', 'previous_1h_std_liters'
    ]
    
    num_scaler = StandardScaler() if scaler_type == 'standard' else RobustScaler()
    
    numeric_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', num_scaler)
    ])
    
    categorical_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer([
        ('num', numeric_pipe, numeric_cols),
        ('cat', categorical_pipe, categorical_cols)
    ], remainder='drop')
    
    return preprocessor, numeric_cols, categorical_cols


def build_leak_preprocessor(scaler_type='standard'):
    """
    Build scikit-learn preprocessor pipeline for leak identification.
    Categorical: zone_type
    Numeric: hydraulic and sensor measurements
    """
    categorical_cols = ['zone_type']
    numeric_cols = [
        'hour', 'occupancy', 'scheduled_activity',
        'inlet_flow_lpm', 'pressure_bar', 'tank_level_pct',
        'previous_1h_avg_flow_lpm', 'previous_1h_avg_pressure_bar',
        'flow_change_lpm', 'pressure_change_bar'
    ]
    
    num_scaler = StandardScaler() if scaler_type == 'standard' else RobustScaler()
    
    numeric_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', num_scaler)
    ])
    
    categorical_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
    ])
    
    preprocessor = ColumnTransformer([
        ('num', numeric_pipe, numeric_cols),
        ('cat', categorical_pipe, categorical_cols)
    ], remainder='drop')
    
    return preprocessor, numeric_cols, categorical_cols
