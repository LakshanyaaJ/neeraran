import pandas as pd
import numpy as np
import json

print("--- Inspecting Abnormal Consumption Dataset ---")
df_abn = pd.read_csv("data/synthetic/abnormal_consumption.csv")
print(f"Abnormal shape: {df_abn.shape}")
print("Columns:", list(df_abn.columns))
print("Missing values:")
print(df_abn.isnull().sum()[df_abn.isnull().sum() > 0])
print(f"Duplicates: {df_abn.duplicated().sum()}")
print(f"Meters ({df_abn['meter_id'].nunique()}): {df_abn['meter_id'].unique()}")
print(f"Zones ({df_abn['zone_id'].nunique()}): {df_abn['zone_id'].unique()}")
print(f"Campuses: {df_abn['campus_id'].unique()}")
print("is_anomaly distribution:")
print(df_abn['is_anomaly'].value_counts(dropna=False))
print("anomaly_type distribution:")
print(df_abn['anomaly_type'].value_counts(dropna=False))
print(f"Unique event_id: {df_abn['event_id'].nunique()} (nulls: {df_abn['event_id'].isnull().sum()})")
print("Min timestamp:", df_abn['timestamp'].min(), "Max timestamp:", df_abn['timestamp'].max())

print("\n--- Inspecting Leak Identification Dataset ---")
df_leak = pd.read_csv("data/synthetic/leak_identification.csv")
print(f"Leak shape: {df_leak.shape}")
print("Columns:", list(df_leak.columns))
print("Missing values:")
print(df_leak.isnull().sum()[df_leak.isnull().sum() > 0])
print(f"Duplicates: {df_leak.duplicated().sum()}")
print(f"Meters ({df_leak['meter_id'].nunique()}): {df_leak['meter_id'].unique()}")
print(f"Zones ({df_leak['zone_id'].nunique()}): {df_leak['zone_id'].unique()}")
print("event_label distribution:")
print(df_leak['event_label'].value_counts(dropna=False))
print("event_type distribution:")
print(df_leak['event_type'].value_counts(dropna=False))
print("Cross-tab event_label vs event_type:")
print(pd.crosstab(df_leak['event_label'], df_leak['event_type'].fillna('NONE'), dropna=False))
print(f"Unique event_id: {df_leak['event_id'].nunique()} (nulls: {df_leak['event_id'].isnull().sum()})")
print("Min timestamp:", df_leak['timestamp'].min(), "Max timestamp:", df_leak['timestamp'].max())

# Compare event_ids
abn_events = set(df_abn['event_id'].dropna().unique())
leak_events = set(df_leak['event_id'].dropna().unique())
print(f"\nAbnormal events count: {len(abn_events)}, Leak events count: {len(leak_events)}")
print(f"Shared events count: {len(abn_events.intersection(leak_events))}")
print(f"Abnormal only: {len(abn_events - leak_events)}, Leak only: {len(leak_events - abn_events)}")

# Check event type matching
shared = abn_events.intersection(leak_events)
sample_shared = list(shared)[:5]
print("\nSample shared events comparison:")
for eid in sample_shared:
    sub_a = df_abn[df_abn['event_id'] == eid]
    sub_l = df_leak[df_leak['event_id'] == eid]
    print(f"Event {eid}:")
    print(f"  Abnormal: {len(sub_a)} rows, zones={sub_a['zone_id'].unique()}, meter={sub_a['meter_id'].unique()}, types={sub_a['anomaly_type'].unique()}, time=[{sub_a['timestamp'].min()} to {sub_a['timestamp'].max()}]")
    print(f"  Leak:     {len(sub_l)} rows, zones={sub_l['zone_id'].unique()}, meter={sub_l['meter_id'].unique()}, types={sub_l['event_type'].unique()}, labels={sub_l['event_label'].unique()}, time=[{sub_l['timestamp'].min()} to {sub_l['timestamp'].max()}]")
