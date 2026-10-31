import pandas as pd
import numpy as np

df_abn = pd.read_csv("data/synthetic/abnormal_consumption.csv")
df_leak = pd.read_csv("data/synthetic/leak_identification.csv")

print("--- Abnormal Missing Value Inspection ---")
for col in df_abn.columns:
    n_miss = df_abn[col].isnull().sum()
    if n_miss > 0:
        times = df_abn[df_abn[col].isnull()]['timestamp'].unique()
        print(f"Col {col}: {n_miss} nulls, timestamps: {times[:3]} (total {len(times)} timestamps)")

print("\n--- Leak Missing Value Inspection ---")
for col in df_leak.columns:
    n_miss = df_leak[col].isnull().sum()
    if n_miss > 0:
        evt_types = df_leak[df_leak[col].isnull()]['event_type'].value_counts().to_dict()
        times = df_leak[df_leak[col].isnull()]['timestamp'].unique()
        print(f"Col {col}: {n_miss} nulls, event_types: {evt_types}, timestamps count: {len(times)}, sample: {times[:3]}")

# Check meter-wise distribution
print("\n--- Meter Counts ---")
print("Abnormal meters:")
print(df_abn['meter_id'].value_counts())
print("Leak meters:")
print(df_leak['meter_id'].value_counts())

# Check timestamp continuity
df_abn['timestamp'] = pd.to_datetime(df_abn['timestamp'])
df_leak['timestamp'] = pd.to_datetime(df_leak['timestamp'])

for mid in df_abn['meter_id'].unique()[:3]:
    sub = df_abn[df_abn['meter_id'] == mid].sort_values('timestamp')
    diffs = sub['timestamp'].diff().dropna()
    print(f"Meter {mid} unique time steps: {diffs.value_counts().to_dict()}")

# Check event distribution across zones
print("\n--- Event Distribution across Zones ---")
abn_evt_zone = df_abn.dropna(subset=['event_id']).groupby('zone_id')['event_id'].nunique()
print("Abnormal unique events per zone:")
print(abn_evt_zone)

leak_evt_zone = df_leak.dropna(subset=['event_id']).groupby('zone_id')['event_id'].nunique()
print("Leak unique events per zone:")
print(leak_evt_zone)

# Check distribution of event types per event_id
evt_meta = df_leak.dropna(subset=['event_id']).groupby('event_id').agg({
    'timestamp': ['min', 'max', 'count'],
    'event_label': 'first',
    'event_type': 'first',
    'meter_id': 'first',
    'zone_id': 'first'
})
evt_meta.columns = ['start', 'end', 'row_count', 'event_label', 'event_type', 'meter_id', 'zone_id']
print("\n--- Event Metadata Summary ---")
print(evt_meta.head(10))
print("\nEvent counts per label:")
print(evt_meta['event_label'].value_counts())
print("\nEvent counts per type:")
print(evt_meta['event_type'].value_counts())
