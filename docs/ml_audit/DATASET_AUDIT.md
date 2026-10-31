# AquaGuard AI — Dataset Audit Report

**Auditor:** Senior Machine Learning Auditor & Statistical Validation Specialist  
**Audit Date:** October 31, 2026  
**Audited Datasets:**
1. `data/synthetic/abnormal_consumption.csv`
2. `data/synthetic/leak_identification.csv`

---

## 1. Dataset Inventory and Verification

Both datasets were verified against physical files in the repository.

| Metric | Abnormal Consumption Dataset | Leak Identification Dataset | Verification Status |
|---|---|---|:---:|
| **File Path** | `data/synthetic/abnormal_consumption.csv` | `data/synthetic/leak_identification.csv` | Confirmed Present |
| **Backup Path** | `data/backup/abnormal_consumption_backup.csv` | `data/backup/leak_identification_backup.csv` | Confirmed Secured |
| **Row Count** | 311,040 rows | 311,040 rows | Exact Match |
| **Column Count** | 28 columns (20 base + 8 sensor status) | 27 columns (19 base + 8 sensor status) | Exact Match |
| **Time Span** | 2026-07-01 00:00:00 to 2026-09-28 23:55:00 | 2026-07-01 00:00:00 to 2026-09-28 23:55:00 | Exactly 90 Days |
| **Sampling Cadence** | Continuous 5-minute intervals | Continuous 5-minute intervals | Zero Missing Timesteps |
| **Monitored Meters** | 12 meters (`M01` to `M12`) | 12 meters (`M01` to `M12`) | 25,920 rows per meter |
| **Campus Zones** | 6 campus zones | 6 campus zones | Complete Alignment |
| **Total Injected Events** | 77 events (`EVT_0001` to `EVT_0077`) | 77 events (`EVT_0001` to `EVT_0077`) | 100% Event ID Alignment |

---

## 2. Schema and Column Breakdown

### 2.1 Abnormal Consumption Dataset Schema (`abnormal_consumption.csv`)

| Column Name | Data Type | Non-Null Count | Missing | Domain / Description |
|---|---|---|---|---|
| `timestamp` | Datetime64 | 311,040 | 0 | 5-minute SCADA observation timestamp |
| `campus_id` | String | 311,040 | 0 | University identifier (`CAMPUS_01`) |
| `zone_id` | String | 311,040 | 0 | Zonal identifier (`ZONE_HOSTEL`, etc.) |
| `zone_type` | String | 311,040 | 0 | Categorical facility type (6 categories) |
| `meter_id` | String | 311,040 | 0 | Smart meter hardware ID (`M01` to `M12`) |
| `hour` | Integer | 311,040 | 0 | Diurnal hour (0 to 23) |
| `day_of_week` | Integer | 311,040 | 0 | Day index (0 = Monday, 6 = Sunday) |
| `is_weekend` | Integer | 311,040 | 0 | Binary indicator (0 = Weekday, 1 = Weekend) |
| `is_holiday` | Integer | 311,040 | 0 | Academic holiday indicator (0 or 1) |
| `occupancy` | Integer | 311,040 | 0 | Estimated person count in zone |
| `scheduled_activity` | Integer | 311,040 | 0 | Scheduled high-demand event flag (0 or 1) |
| `temperature_c` | Float | 311,040 | 0 | Ambient outdoor temperature in Celsius |
| `interval_consumption_liters` | Float | 311,040 | 0 | Volumetric consumption in 5-min window |
| `previous_1h_avg_liters` | Float | 311,028 | 12 | Rolling 1-hour lookback mean consumption |
| `previous_24h_avg_liters` | Float | 311,028 | 12 | Rolling 24-hour lookback mean consumption |
| `previous_1h_std_liters` | Float | 311,028 | 12 | Rolling 1-hour lookback standard deviation |
| `is_anomaly` | Integer | 311,040 | 0 | Ground truth binary anomaly target (0 / 1) |
| `anomaly_type` | String | 311,040 | 0 | Sub-type of consumption anomaly |
| `event_id` | String | 1,007 | 310,033 | Injected incident identifier |
| `source` | String | 311,040 | 0 | Data provenance (`synthetic_scada`) |
| `sensor_power_status` | String | 311,040 | 0 | Device power state (`ON`, `OFF`) |
| `sensor_connectivity_status`| String | 311,040 | 0 | Gateway link (`CONNECTED`, `DISCONNECTED`)|
| `sensor_health_status` | String | 311,040 | 0 | Sensor state (`HEALTHY`, `OFFLINE`, etc.) |
| `last_reading_timestamp` | Datetime64 | 311,040 | 0 | Timestamp of last received packet |
| `reading_received` | Integer | 311,040 | 0 | Transmission flag (1 = received, 0 = missing)|
| `missing_reading_count` | Integer | 311,040 | 0 | Consecutive missing reading counter |
| `sensor_battery_pct` | Float | 311,040 | 0 | Battery level (0 to 100%) |
| `sensor_fault_type` | String | 311,040 | 0 | Physical fault mode (`NONE`, `SENSOR_STUCK`)|

---

## 3. Target Label Semantics & Distribution

### 3.1 Abnormal Consumption Target (`is_anomaly`)
- **Class 0 (Normal):** 310,033 records (99.676%)
- **Class 1 (Anomaly):** 1,007 records (0.324%)
- **Imbalance Ratio:** 307.9 to 1

#### Anomaly Type Breakdown:
| Anomaly Type | Record Count | Description |
|---|---|---|
| `normal` | 310,033 | Regular diurnal campus water consumption |
| `leak_related_unusual_consumption` | 841 | Continuous, uncharacteristic off-peak volume |
| `unexpected_low_occupancy_continuous_use` | 150 | Night-time dorm consumption without occupancy |
| `unexpected_spike` | 16 | Sudden sharp volumetric surge |

### 3.2 Leak Identification Target (`event_label`)
An exhaustive audit of `event_label` and `event_type` revealed the actual mapping implemented in the codebase:

| `event_label` | Codebase Semantics | Underlying `event_type` Values | Record Count | Percentage |
|:---:|---|---|---|---|
| **0** | **Baseline / Non-Leak** | `normal` (309,512), `night_use` (150), `unexpected_spike` (16) | 309,678 | 99.562% |
| **1** | **Physical Pipe Leak** | `leak_moderate` (343), `leak_intermittent` (222), `leak_small` (200), `leak_major` (76) | 841 | 0.270% |
| **2** | **Demand Surge** | `demand_hostel` (114), `demand_canteen` (104), `cleaning` (72) | 290 | 0.093% |
| **3** | **Sensor / Instrument Fault** | `sensor_drift` (148), `sensor_stuck` (52), `sensor_missing` (21), `sensor_spike` (10) | 231 | 0.074% |

> [!IMPORTANT]
> **Audit Finding (AUD-003):** The prompt states that Model 2 predicts 4 classes: 0 = Normal, 1 = Minor leak, 2 = Major leak, 3 = Burst pipe. The actual codebase and dataset map Class 1 to **all physical leaks** (small, moderate, major, intermittent), Class 2 to **Demand Surges**, and Class 3 to **Sensor Faults**. This design was intentionally structured to differentiate physical leaks from benign demand peaks and sensor instrumentation errors.

---

## 4. Missing Values Audit & Root Causes

A comprehensive audit identified exactly two sources of missing values:

1. **Cold-Start Lookback Nulls (12 rows per rolling feature):**
   - At timestamp $t_0$ (`2026-07-01 00:00:00`), each of the 12 meters lacks historical observations.
   - Affects `previous_1h_avg_liters`, `previous_24h_avg_liters`, `previous_1h_avg_flow_lpm`, and `previous_1h_avg_pressure_bar`.
   - Properly imputed using training-partition median via scikit-learn `SimpleImputer`.
2. **Simulated Telemetry Loss (21 rows in `inlet_flow_lpm`):**
   - Occurs strictly during event `EVT_0070` (`sensor_missing`, Meter `M03`, Zone `ACADEMIC`).
   - Represents wireless packet loss. Handled via `SimpleImputer` inside `ColumnTransformer`.
   - Missing readings are represented as `NaN`, never replaced with zero water consumption.

---

## 5. Synthetic Dataset Artifacts & Realism Limitations

1. **Deterministic Diurnal Profiles:** Base consumption is synthesized using sinusoidal curves modulated by schedule and occupancy. Real campuses experience higher non-deterministic variance (e.g. sporadic lab experiments, seasonal irrigation).
2. **Perfect Meter Cadence:** In real hardware, packet arrival times jitter (e.g. 4.8 min to 5.4 min) due to cellular queueing. The synthetic dataset has clock-perfect 5.0-minute timestamps.
3. **Discrete Event Injections:** Injected leaks have crisp step-function or trapezoidal boundaries. Real subterranean pipe leaks often begin with micro-fissures that degrade over weeks before catastrophic rupture.
