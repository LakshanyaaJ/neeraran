"""
AquaGuard AI - Data Loader and Preprocessing Pipeline
Handles data loading, validation, missing value imputation, and chronological event-aware splitting.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, List

import os

def get_data_paths() -> Tuple[str, str]:
    if os.path.exists("data/synthetic/abnormal_consumption.csv"):
        return "data/synthetic/abnormal_consumption.csv", "data/synthetic/leak_identification.csv"
    elif os.path.exists("../data/synthetic/abnormal_consumption.csv"):
        return "../data/synthetic/abnormal_consumption.csv", "../data/synthetic/leak_identification.csv"
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "data", "synthetic", "abnormal_consumption.csv"), os.path.join(base, "data", "synthetic", "leak_identification.csv")


# User-specified initial candidate features
ABNORMAL_CANDIDATE_FEATURES = [
    'zone_type', 'hour', 'day_of_week', 'is_weekend', 'is_holiday',
    'occupancy', 'scheduled_activity', 'temperature_c',
    'interval_consumption_liters', 'previous_1h_avg_liters',
    'previous_24h_avg_liters', 'previous_1h_std_liters'
]

LEAK_CANDIDATE_FEATURES = [
    'zone_type', 'hour', 'occupancy', 'scheduled_activity',
    'inlet_flow_lpm', 'pressure_bar', 'tank_level_pct',
    'previous_1h_avg_flow_lpm', 'previous_1h_avg_pressure_bar',
    'flow_change_lpm', 'pressure_change_bar'
]

# Explicitly disallowed features as per specification
DISALLOWED_ABNORMAL = ['is_anomaly', 'anomaly_type', 'event_id', 'meter_id', 'zone_id', 'campus_id', 'source']
DISALLOWED_LEAK = ['event_label', 'event_type', 'event_id', 'meter_id', 'zone_id', 'campus_id', 'source']


def load_raw_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load both datasets directly without altering original files."""
    abnormal_path, leak_path = get_data_paths()
    df_abnormal = pd.read_csv(abnormal_path)
    df_leak = pd.read_csv(leak_path)
    
    df_abnormal['timestamp'] = pd.to_datetime(df_abnormal['timestamp'])
    df_leak['timestamp'] = pd.to_datetime(df_leak['timestamp'])
    
    return df_abnormal, df_leak


def get_chronological_cutoffs(timestamps: pd.Series, train_ratio: float = 0.70, val_ratio: float = 0.15) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Calculate exact timestamp cutoffs for 70% / 15% / 15% chronological split."""
    t_min = timestamps.min()
    t_max = timestamps.max()
    total_duration = (t_max - t_min).total_seconds()
    
    cutoff_train = t_min + pd.Timedelta(seconds=total_duration * train_ratio)
    cutoff_val = t_min + pd.Timedelta(seconds=total_duration * (train_ratio + val_ratio))
    
    return cutoff_train, cutoff_val


def split_dataset_event_aware(df: pd.DataFrame, train_ratio: float = 0.70, val_ratio: float = 0.15) -> Dict[str, Any]:
    """
    Vectorized chronological event-aware split:
    - Events are kept completely intact within a single partition.
    - Records without event_id are partitioned by timestamp.
    - Zero event overlap between partitions.
    """
    cutoff_train, cutoff_val = get_chronological_cutoffs(df['timestamp'], train_ratio, val_ratio)
    
    # Event metadata
    events = df.dropna(subset=['event_id']).groupby('event_id').agg(
        start=('timestamp', 'min'),
        end=('timestamp', 'max')
    ).reset_index()
    
    def assign_event(row):
        if row['end'] <= cutoff_train:
            return 'train'
        elif row['start'] >= cutoff_val:
            return 'test'
        elif row['start'] >= cutoff_train and row['end'] <= cutoff_val:
            return 'val'
        elif row['start'] < cutoff_train and row['end'] > cutoff_train:
            return 'train'
        else:
            return 'val'
            
    events['split'] = events.apply(assign_event, axis=1)
    event_split_dict = dict(zip(events['event_id'], events['split']))
    
    # Vectorized assignment
    splits = pd.Series('unassigned', index=df.index)
    has_event = df['event_id'].notnull()
    splits[has_event] = df.loc[has_event, 'event_id'].map(event_split_dict)
    
    no_event = ~has_event
    splits[no_event & (df['timestamp'] < cutoff_train)] = 'train'
    splits[no_event & (df['timestamp'] >= cutoff_train) & (df['timestamp'] < cutoff_val)] = 'val'
    splits[no_event & (df['timestamp'] >= cutoff_val)] = 'test'
    
    df_copy = df.copy()
    df_copy['split'] = splits
    
    train_df = df_copy[df_copy['split'] == 'train'].drop(columns=['split'])
    val_df = df_copy[df_copy['split'] == 'val'].drop(columns=['split'])
    test_df = df_copy[df_copy['split'] == 'test'].drop(columns=['split'])
    
    return {
        'train': train_df,
        'val': val_df,
        'test': test_df,
        'cutoffs': (cutoff_train, cutoff_val),
        'event_split_map': event_split_dict
    }
