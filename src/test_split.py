import pandas as pd
import numpy as np

df_leak = pd.read_csv("data/synthetic/leak_identification.csv")
df_leak['timestamp'] = pd.to_datetime(df_leak['timestamp'])

# Check event start timestamps
events = df_leak.dropna(subset=['event_id']).groupby('event_id').agg(
    start=('timestamp', 'min'),
    end=('timestamp', 'max'),
    event_label=('event_label', 'first'),
    event_type=('event_type', 'first'),
    rows=('event_id', 'count')
).reset_index()

t_min = df_leak['timestamp'].min()
t_max = df_leak['timestamp'].max()
total_sec = (t_max - t_min).total_seconds()

split_t1 = t_min + pd.Timedelta(seconds=total_sec * 0.70)
split_t2 = t_min + pd.Timedelta(seconds=total_sec * 0.85)

print(f"Time range: {t_min} to {t_max}")
print(f"Split cutoff 1 (70%): {split_t1}")
print(f"Split cutoff 2 (85%): {split_t2}")

# Assign events to split based on event start time (or event overlap)
def assign_event_split(row):
    # event must be wholly or primarily in partition
    if row['end'] <= split_t1:
        return 'train'
    elif row['start'] >= split_t2:
        return 'test'
    elif row['start'] >= split_t1 and row['end'] <= split_t2:
        return 'val'
    elif row['start'] < split_t1 and row['end'] > split_t1:
        return 'train' # straddles cutoff 1
    else:
        return 'val' # straddles cutoff 2

events['split'] = events.apply(assign_event_split, axis=1)
print("\nEvent count by split and event_label:")
print(pd.crosstab(events['split'], events['event_label']))
print("\nEvent count by split and event_type:")
print(pd.crosstab(events['split'], events['event_type']))
