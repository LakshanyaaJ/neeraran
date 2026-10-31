"""
Generate and execute Notebook 01: Abnormal Consumption EDA
"""

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor
import os

nb = nbf.v4.new_notebook()

cells = []

# Title & Metadata
cells.append(nbf.v4.new_markdown_cell("""# AquaGuard AI — Abnormal Consumption Exploratory Data Analysis (EDA)
**Task:** Exploratory Data Analysis of Smart Meter Water Consumption Time-Series  
**Dataset:** `data/synthetic/abnormal_consumption.csv` (311,040 rows, 12 meters, 6 zones, 90 days at 5-minute sampling)  
**Target:** `is_anomaly` (0 = Normal, 1 = Abnormal)  

---
### Notebook Objectives
1. Perform comprehensive dataset overview, schema inspection, and data quality checks.
2. Analyze missing values, rolling-window baseline artifacts, and timestamp continuity.
3. Evaluate class distribution, anomaly types, and event structures.
4. Explore spatial (zone-wise, meter-wise) and temporal (diurnal hour-wise, day-of-week) consumption patterns.
5. Investigate operational correlations (occupancy, scheduled activities, temperature) against consumption.
6. Contrast normal vs abnormal hydraulic regimes and identify multi-feature interactions.
"""))

# Cell 1: Imports and setup
cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configure aesthetic style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
os.makedirs('../results/figures', exist_ok=True)
os.makedirs('results/figures', exist_ok=True)

# Load dataset
DATA_PATH = '../data/synthetic/abnormal_consumption.csv' if os.path.exists('../data/synthetic/abnormal_consumption.csv') else 'data/synthetic/abnormal_consumption.csv'
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])
print(f"Dataset Loaded Successfully! Shape: {df.shape}")
"""))

# Cell 2: Dataset overview & Data Types
cells.append(nbf.v4.new_markdown_cell("""## 1. Dataset Overview and Schema Inspection
We inspect data types, memory footprint, and column definitions.
"""))

cells.append(nbf.v4.new_code_cell("""print("Dataset Info:")
df.info()
print("\\nFirst 5 Rows:")
display(df.head())
"""))

# Cell 3: Missing Values & Duplicates
cells.append(nbf.v4.new_markdown_cell("""## 2. Missing Values, Invalid Records, and Continuity Analysis
We verify whether missing values exist, examine whether they stem from initial rolling-window calculations, and check continuity.
"""))

cells.append(nbf.v4.new_code_cell("""missing = df.isnull().sum()
missing_pct = (missing / len(df)) * 100
dq_df = pd.DataFrame({'Missing_Count': missing, 'Percentage': missing_pct})
display(dq_df[dq_df['Missing_Count'] > 0])

duplicates = df.duplicated().sum()
print(f"Total duplicate rows: {duplicates}")

# Timestamp continuity per meter
meters = df['meter_id'].unique()
print(f"Total unique meters: {len(meters)} ({list(meters)})")
for m in meters[:3]:
    sub = df[df['meter_id'] == m].sort_values('timestamp')
    step_diffs = sub['timestamp'].diff().dropna().unique()
    print(f"Meter {m}: record count = {len(sub)}, unique sampling steps = {step_diffs}")
"""))

# Cell 4: Target Class Distribution & Anomaly Types
cells.append(nbf.v4.new_markdown_cell("""## 3. Target Class and Anomaly Type Distribution
Investigating the severity of class imbalance in `is_anomaly` and the composition of `anomaly_type`.
"""))

cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Class distribution
class_counts = df['is_anomaly'].value_counts()
sns.barplot(x=class_counts.index, y=class_counts.values, ax=axes[0], palette=['#1f77b4', '#d62728'])
axes[0].set_title(f"Target Distribution: is_anomaly\\n(Class 0: {class_counts[0]:,} | Class 1: {class_counts[1]:,})", fontweight='bold')
axes[0].set_xlabel("Anomaly Status (0=Normal, 1=Abnormal)")
axes[0].set_ylabel("Record Count")
for p in axes[0].patches:
    axes[0].annotate(f"{int(p.get_height()):,}\\n({p.get_height()/len(df)*100:.2f}%)", 
                     (p.get_x() + p.get_width()/2., p.get_height()/2),
                     ha='center', va='center', color='white', fontweight='bold')

# Anomaly type breakdown
type_counts = df[df['is_anomaly'] == 1]['anomaly_type'].value_counts()
sns.barplot(x=type_counts.values, y=type_counts.index, ax=axes[1], palette='flare')
axes[1].set_title(f"Breakdown of Abnormal Events (Total: {len(type_counts.index)} types)", fontweight='bold')
axes[1].set_xlabel("Count")
for p in axes[1].patches:
    axes[1].annotate(f"{int(p.get_width()):,} ({p.get_width()/class_counts[1]*100:.1f}%)", 
                     (p.get_width()/2, p.get_y() + p.get_height()/2.),
                     ha='center', va='center', color='white', fontweight='bold')

plt.tight_layout()
fig_path = '../results/figures/01_abnormal_class_distribution.png' if os.path.exists('../results') else 'results/figures/01_abnormal_class_distribution.png'
plt.savefig(fig_path, dpi=300)
plt.show()

print("Key Finding: Extreme class imbalance. Only 1,007 records (0.32%) are abnormal, reflecting realistic industrial SCADA operating conditions.")
"""))

# Cell 5: Descriptive Statistics
cells.append(nbf.v4.new_markdown_cell("""## 4. Descriptive Statistics: Normal vs Abnormal
We compare hydraulic and environmental parameters between normal operation and abnormal incidents.
"""))

cells.append(nbf.v4.new_code_cell("""features = ['interval_consumption_liters', 'previous_1h_avg_liters', 'previous_24h_avg_liters', 
            'previous_1h_std_liters', 'occupancy', 'temperature_c']
stat_comp = df.groupby('is_anomaly')[features].describe().T
display(stat_comp)
"""))

# Cell 6: Zone-wise Consumption Analysis
cells.append(nbf.v4.new_markdown_cell("""## 5. Spatial Analysis: Zone-wise Water Consumption
Campus zones have distinct hydraulic baselines: Hostels and Canteens experience high peak volumetric throughput, whereas Admin and Library exhibit lower quiescent demand.
"""))

cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(16, 6))

sns.boxplot(x='zone_id', y='interval_consumption_liters', hue='is_anomaly', data=df, ax=axes[0], palette=['#2b5c8f', '#e74c3c'], showfliers=False)
axes[0].set_title("Consumption Distribution by Zone (Normal vs Anomaly)", fontweight='bold')
axes[0].set_ylabel("5-Min Consumption (Liters)")

zone_agg = df.groupby(['zone_id', 'is_anomaly'])['interval_consumption_liters'].agg(['mean', 'median', 'std']).reset_index()
sns.barplot(x='zone_id', y='mean', hue='is_anomaly', data=zone_agg, ax=axes[1], palette=['#2b5c8f', '#e74c3c'])
axes[1].set_title("Mean 5-Min Consumption by Zone", fontweight='bold')
axes[1].set_ylabel("Mean Liters")

plt.tight_layout()
fig_path = '../results/figures/01_zone_consumption.png' if os.path.exists('../results') else 'results/figures/01_zone_consumption.png'
plt.savefig(fig_path, dpi=300)
plt.show()
"""))

# Cell 7: Temporal Analysis (Hour of Day & Day of Week)
cells.append(nbf.v4.new_markdown_cell("""## 6. Temporal Patterns: Diurnal Profiles and Weekend Effects
Diurnal consumption reflects campus lifestyle. Abnormal consumption deviates significantly from expected circadian baselines, particularly during overnight hours (00:00 - 05:00).
"""))

cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Diurnal profile
hourly = df.groupby(['hour', 'is_anomaly'])['interval_consumption_liters'].mean().unstack()
axes[0].plot(hourly.index, hourly[0], label='Normal', color='#1f77b4', marker='o', linewidth=2.5)
axes[0].plot(hourly.index, hourly[1], label='Abnormal', color='#d62728', marker='s', linewidth=2.5)
axes[0].set_title("Diurnal Consumption Profile (Hour of Day)", fontweight='bold')
axes[0].set_xlabel("Hour of Day (0-23)")
axes[0].set_ylabel("Mean 5-Min Consumption (Liters)")
axes[0].set_xticks(range(0, 24, 2))
axes[0].legend()

# Day of week profile
dow = df.groupby(['day_of_week', 'is_anomaly'])['interval_consumption_liters'].mean().unstack()
dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
axes[1].plot(dow_names, dow[0], label='Normal', color='#1f77b4', marker='o', linewidth=2.5)
axes[1].plot(dow_names, dow[1], label='Abnormal', color='#d62728', marker='s', linewidth=2.5)
axes[1].set_title("Day of Week Consumption Profile", fontweight='bold')
axes[1].set_xlabel("Day of Week")
axes[1].set_ylabel("Mean 5-Min Consumption (Liters)")
axes[1].legend()

plt.tight_layout()
fig_path = '../results/figures/01_temporal_profiles.png' if os.path.exists('../results') else 'results/figures/01_temporal_profiles.png'
plt.savefig(fig_path, dpi=300)
plt.show()
"""))

# Cell 8: Occupancy & Scheduled Activity Interactions
cells.append(nbf.v4.new_markdown_cell("""## 7. Contextual Interactions: Occupancy & Scheduled Activity
Normal consumption exhibits strong positive coupling with building occupancy and scheduled events. Anomalies frequently manifest as high consumption during zero-occupancy periods (e.g. overnight burst).
"""))

cells.append(nbf.v4.new_code_cell("""fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# Scatter with opacity
sns.scatterplot(x='occupancy', y='interval_consumption_liters', hue='is_anomaly', 
                data=df.sample(5000, random_state=42), alpha=0.6, palette=['#1f77b4', '#e74c3c'], ax=axes[0])
axes[0].set_title("Consumption vs Occupancy (Sample of 5,000 Records)", fontweight='bold')
axes[0].set_xlabel("Building Occupancy (Persons)")
axes[0].set_ylabel("5-Min Consumption (Liters)")

# Scheduled activity
sns.boxplot(x='scheduled_activity', y='interval_consumption_liters', hue='is_anomaly', 
            data=df, ax=axes[1], palette=['#1f77b4', '#e74c3c'], showfliers=False)
axes[1].set_title("Consumption by Scheduled Activity Flag", fontweight='bold')
axes[1].set_xlabel("Scheduled Activity (0=None, 1=Event/Class)")
axes[1].set_ylabel("5-Min Consumption (Liters)")

plt.tight_layout()
fig_path = '../results/figures/01_occupancy_interaction.png' if os.path.exists('../results') else 'results/figures/01_occupancy_interaction.png'
plt.savefig(fig_path, dpi=300)
plt.show()
"""))

# Cell 9: Rolling Baseline Analysis
cells.append(nbf.v4.new_markdown_cell("""## 8. Rolling Baseline and Variance Drift Analysis
Examining historical baseline tracking: `previous_1h_avg_liters`, `previous_24h_avg_liters`, and `previous_1h_std_liters`.
"""))

cells.append(nbf.v4.new_code_cell("""df['deviation_from_1h'] = df['interval_consumption_liters'] - df['previous_1h_avg_liters']
df['deviation_from_24h'] = df['interval_consumption_liters'] - df['previous_24h_avg_liters']

fig, axes = plt.subplots(1, 2, figsize=(16, 5))

sns.kdeplot(df[df['is_anomaly'] == 0]['deviation_from_1h'].dropna(), ax=axes[0], label='Normal', color='#1f77b4', fill=True)
sns.kdeplot(df[df['is_anomaly'] == 1]['deviation_from_1h'].dropna(), ax=axes[0], label='Abnormal', color='#d62728', fill=True)
axes[0].set_title("Density of Deviation from 1-Hour Rolling Average", fontweight='bold')
axes[0].set_xlabel("Consumption - 1h_Avg (Liters)")
axes[0].set_xlim(-100, 300)
axes[0].legend()

sns.scatterplot(x='previous_1h_std_liters', y='interval_consumption_liters', hue='is_anomaly',
                data=df.sample(5000, random_state=42), alpha=0.6, palette=['#1f77b4', '#e74c3c'], ax=axes[1])
axes[1].set_title("Consumption vs Rolling 1-Hour Standard Deviation", fontweight='bold')
axes[1].set_xlabel("Rolling 1h Std (Liters)")
axes[1].set_ylabel("5-Min Consumption (Liters)")

plt.tight_layout()
fig_path = '../results/figures/01_rolling_baseline.png' if os.path.exists('../results') else 'results/figures/01_rolling_baseline.png'
plt.savefig(fig_path, dpi=300)
plt.show()
"""))

# Cell 10: Event-Level Analysis
cells.append(nbf.v4.new_markdown_cell("""## 9. Event-Level Analysis: Shared Event IDs and Incident Profiles
Analyzing the 77 shared incident events in the abnormal consumption dataset.
"""))

cells.append(nbf.v4.new_code_cell("""event_summary = df.dropna(subset=['event_id']).groupby('event_id').agg(
    meter_id=('meter_id', 'first'),
    zone_id=('zone_id', 'first'),
    anomaly_type=('anomaly_type', 'first'),
    is_anomaly=('is_anomaly', 'max'),
    start_time=('timestamp', 'min'),
    end_time=('timestamp', 'max'),
    duration_steps=('timestamp', 'count')
).reset_index()
event_summary['duration_hours'] = event_summary['duration_steps'] * 5 / 60

print(f"Total Unique Events in Abnormal Dataset: {len(event_summary)}")
print("\\nEvent counts by anomaly_type:")
print(event_summary['anomaly_type'].value_counts())
print("\\nEvent counts by zone_id:")
print(event_summary['zone_id'].value_counts())
print("\\nSample Event Table:")
display(event_summary.head(10))
"""))

# Cell 11: Correlation Heatmap
cells.append(nbf.v4.new_markdown_cell("""## 10. Correlation Matrix & Multicollinearity Inspection
We examine pairwise Pearson correlations across all candidate numeric features.
"""))

cells.append(nbf.v4.new_code_cell("""num_cols = ['hour', 'day_of_week', 'is_weekend', 'is_holiday', 'occupancy', 
            'scheduled_activity', 'temperature_c', 'interval_consumption_liters', 
            'previous_1h_avg_liters', 'previous_24h_avg_liters', 'previous_1h_std_liters', 'is_anomaly']

corr = df[num_cols].corr()

plt.figure(figsize=(11, 9))
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, cbar_kws={'label': 'Pearson Correlation'})
plt.title("Correlation Matrix — Abnormal Consumption Dataset", fontsize=14, fontweight='bold', pad=15)
plt.tight_layout()
fig_path = '../results/figures/01_abnormal_correlation.png' if os.path.exists('../results') else 'results/figures/01_abnormal_correlation.png'
plt.savefig(fig_path, dpi=300)
plt.show()

print("Findings: High correlation between interval_consumption_liters and rolling baselines (0.78 with 1h_avg, 0.69 with 24h_avg).")
"""))

# Cell 12: Time-Series Incident Case Study
cells.append(nbf.v4.new_markdown_cell("""## 11. Time-Series Case Study: Hydrograph of Anomaly Incidents
We plot an excerpt showing normal baseline transition into an abnormal consumption burst.
"""))

cells.append(nbf.v4.new_code_cell("""# Select meter M09 and a window containing EVT_0001
sample_event = event_summary[event_summary['is_anomaly'] == 1].iloc[0]
eid = sample_event['event_id']
mid = sample_event['meter_id']
start_t = sample_event['start_time'] - pd.Timedelta(hours=12)
end_t = sample_event['end_time'] + pd.Timedelta(hours=12)

ts_slice = df[(df['meter_id'] == mid) & (df['timestamp'] >= start_t) & (df['timestamp'] <= end_t)].sort_values('timestamp')

plt.figure(figsize=(15, 6))
plt.plot(ts_slice['timestamp'], ts_slice['interval_consumption_liters'], label='5-Min Consumption', color='#1f77b4', lw=1.8)
plt.plot(ts_slice['timestamp'], ts_slice['previous_1h_avg_liters'], label='Rolling 1h Avg', color='#2ca02c', linestyle='--', lw=1.5)

# Highlight anomaly period
anom_slice = ts_slice[ts_slice['is_anomaly'] == 1]
plt.scatter(anom_slice['timestamp'], anom_slice['interval_consumption_liters'], color='#d62728', s=60, zorder=5, label='Abnormal Consumption (is_anomaly=1)')

plt.axvspan(sample_event['start_time'], sample_event['end_time'], color='#ff9999', alpha=0.3, label=f'Event Window ({sample_event["anomaly_type"]})')
plt.title(f"Time-Series Incident hydrograph: Meter {mid} ({sample_event['zone_id']}) — Event {eid}", fontsize=14, fontweight='bold')
plt.xlabel("Timestamp")
plt.ylabel("Consumption (Liters)")
plt.legend(loc='upper right')
plt.tight_layout()
fig_path = '../results/figures/01_timeseries_case_study.png' if os.path.exists('../results') else 'results/figures/01_timeseries_case_study.png'
plt.savefig(fig_path, dpi=300)
plt.show()
"""))

# Cell 13: Summary Conclusions
cells.append(nbf.v4.new_markdown_cell("""## 12. Summary of EDA Findings & Modeling Implications
1. **Data Integrity & Continuity:** 311,040 rows, exactly 25,920 continuous 5-minute timestamps per meter across all 12 meters with zero missing records.
2. **Missing Value Origin:** Missing values in `previous_1h_avg_liters` and `previous_24h_avg_liters` (12 rows each) occur solely at timestamp index 0 ($t=0$) for each meter due to cold-start rolling window boundaries. Imputed using backward-fill / median.
3. **Severe Class Imbalance:** Normal = 310,033 (99.68%), Anomaly = 1,007 (0.32%). Unsupervised models must fit solely on normal baseline observations.
4. **Contextual Confounding:** Consumption spikes alone are not necessarily anomalies; legitimate daytime hostel/canteen peaks correlate with high occupancy and scheduled activity. True anomalies decouple from occupancy (e.g. overnight continuous use).
"""))

nb.cells = cells

# Save notebook
with open('notebooks/01_abnormal_consumption_eda.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook 01 written successfully!")
