# AQUAGUARD AI — SENSOR HEALTH MONITORING & MISSING DATA ALERT SYSTEM
## Technical Architecture, Telemetry Specification, and Operational Guide

**Author:** Senior IoT Systems Architect, Data Engineer & ML Systems Engineer  
**Version:** 2.0.0 (Production Release)  
**Target Infrastructure:** 12 Smart Flow Meters, 6 Zonal Campus Facilities, 5-Minute Continuous Sampling  

---

## 1. System Overview and Decoupled Architecture

AquaGuard AI enforces a strict architectural boundary between **Layer 1: Sensor Health & Telemetry Resilience** and **Layer 2: Water Intelligence & Hydraulic Classification**. This prevents missing sensor packets or power outages from being misdiagnosed as physical water pipe bursts.

```
+---------------------------------------------------------------------------------------------------+
|                                AQUAGUARD AI DUAL-ENGINE ARCHITECTURE                              |
+---------------------------------------------------------------------------------------------------+
                                                  │
                                                  ▼
                         5-Minute Raw Telemetry Stream (LoRaWAN / Modbus)
                                                  │
                        ┌─────────────────────────┴─────────────────────────┐
                        │                                                   │
                        ▼                                                   ▼
       ┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
       │   LAYER 1: SENSOR HEALTH        │                 │   LAYER 2: WATER INTELLIGENCE   │
       │   MONITORING SERVICE            │                 │   (Trained ML Decision Trees)   │
       └─────────────────────────────────┘                 └─────────────────────────────────┘
                        │                                                   │
         - Power Status (ON / OFF)                           - Unsupervised Anomaly Engine (OC-SVM)
         - Gateway Connectivity                              - Supervised Multiclass Leak (XGBoost)
         - Missing Reading Counters                          - Physical Pressure/Flow Signature
         - Battery Voltage & Degradation                     - Diurnal Demand Regimes
         - Transducer Malfunctions                           - Dynamic Hydrographs
                        │                                                   │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
                                                  ▼
                               ┌─────────────────────────────────────┐
                               │   EVIDENCE-BASED DECISION ENGINE    │
                               │   (Physics & Telemetry Decoupling)  │
                               └─────────────────────────────────────┘
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 │                                                                 │
                 ▼                                                                 ▼
      [SENSOR HEALTH INCIDENT]                                          [HYDRAULIC WATER ALERT]
 - Warning: 2 Consecutive Missed (10m)                            - Confirmed Leak Burst (Head Loss)
 - Critical: 3+ Consecutive Missed (15m)                          - Legitimate Demand Peak (Preserved)
 - Confirmed OFF vs Inferred OFFLINE                              - Inferred Malfunction Flagged
 - Auto-Recovery: 2 Consecutive Valid                             - INSUFFICIENT_SENSOR_DATA Triggered
                 │                                                                 │
                 └────────────────────────────────┬────────────────────────────────┘
                                                  │
                                                  ▼
                        FastAPI REST Engine ──► Real-Time Frontend Dashboard
```

---

## 2. Enriched Telemetry Columns Specification

Both `data/synthetic/abnormal_consumption.csv` and `data/synthetic/leak_identification.csv` were enhanced with the following eight operational columns:

| Column Name | Data Type | Permitted Values | Operational Semantics |
| :--- | :---: | :--- | :--- |
| `sensor_power_status` | String | `ON`, `OFF` | Device-reported electrical state from internal auxiliary DC or mains feed. |
| `sensor_connectivity_status` | String | `CONNECTED`, `DISCONNECTED` | Gateway or field transmission link status (LoRaWAN RSSI/ACK). |
| `sensor_health_status` | String | `HEALTHY`, `WARNING`, `FAULTY`, `OFFLINE`, `MAINTENANCE` | Consolidated operational state of the sensor node. |
| `last_reading_timestamp` | Datetime | ISO 8601 string (`YYYY-MM-DD HH:MM:SS`) | Timestamp of the most recent valid telemetry transmission. |
| `reading_received` | Integer | `1`, `0` | Packet transmission arrival indicator ($1 = \text{Received}$, $0 = \text{Missing}$). |
| `missing_reading_count` | Integer | $\ge 0$ | Running counter of consecutive missed 5-minute sampling intervals. |
| `sensor_battery_pct` | Float | `0.0` to `100.0` | Remaining battery state of charge (percentage). |
| `sensor_fault_type` | String | `NONE`, `SENSOR_STUCK`, `SENSOR_DRIFT`, `SENSOR_SPIKE`, `SENSOR_MISSING` | Physical transducer or digital signal processing failure classification. |

### Missing Readings Representation Rule
- When `reading_received == 0`, telemetry measurements (`interval_consumption_liters`, `inlet_flow_lpm`, `pressure_bar`) are recorded as **`NaN` (null)** in both CSV datasets.
- **Zero substitution is strictly forbidden.** A flow or consumption of $0.0$ Liters represents zero water usage (a physically meaningful measurement during late night quiescent hours), whereas `NaN` indicates transmission absence.

---

## 3. Sensor Status Lifecycle & State Machine

```
              ┌──────────────────────────┐
              │         HEALTHY          │ ◄─────────────────────────┐
              └──────────────────────────┘                           │
                 │                      │                            │
  Reading Missed │       Transducer     │ Battery <= 20%             │
  (Count = 1)    │       Malfunction    │ or Count = 2               │
                 ▼                      ▼                            │
              ┌──────────────────────────┐                           │ 2 Consecutive
              │         WARNING          │                           │ Valid Readings
              └──────────────────────────┘                           │ (Count = 0)
                 │                      │                            │
  Reading Missed │                      │ Fault Confirmed            │
  (Count >= 3)   │                      ▼                            │
                 │              ┌──────────────────────────┐         │
                 │              │          FAULTY          │ ────────┤
                 ▼              └──────────────────────────┘         │
              ┌──────────────────────────┐                           │
              │         OFFLINE          │ ──────────────────────────┘
              └──────────────────────────┘
                 ▲                      ▲
                 │ Planned              │
                 │ Maintenance          │ Maintenance
                 │ Scheduled            │ Complete
                 ▼                      │
              ┌──────────────────────────┐
              │       MAINTENANCE        │
              └──────────────────────────┘
```

---

## 4. Missing Reading Detection Thresholds & Classification Logic

The system checks sensor health every 5 minutes using the following logic:

```python
IF maintenance_mode == True:
    classify as MAINTENANCE
    (Suppress all critical outage alerts; auto-resolve prior open outage alerts)

ELSE IF sensor_power_status == 'OFF':
    classify as POWER_OFF
    (Confirmed power cutoff: tripped breaker, physical power switch off)

ELSE IF sensor_connectivity_status == 'DISCONNECTED':
    classify as COMMUNICATION_FAILURE
    (Gateway unreachable, radio interference, packet timeout)

ELSE IF reading_received == 0:
    classify as MISSING_READING
    consecutive_missing += 1
    (If count == 2 -> WARNING; if count >= 3 -> OFFLINE)

ELSE IF sensor_fault_type != 'NONE':
    classify as SENSOR_FAULT
    (Hardware failure: SENSOR_STUCK, SENSOR_DRIFT, SENSOR_SPIKE)

ELSE:
    classify as HEALTHY
    consecutive_valid += 1
    consecutive_missing = 0
```

### Confirmed Power OFF vs Inferred OFFLINE
- **Confirmed Power OFF:** The device explicitly transmits an early power-down diagnostic packet before dropping offline, or a power distribution board reports circuit disconnection.
- **Inferred OFFLINE:** The gateway receives no transmission for $\ge 15$ minutes ($\ge 3$ missed intervals) without prior notice. The system marks the sensor `OFFLINE` and escalates to a **Critical Outage Alert**.

---

## 5. Alert Incident Deduplication & Severity Hierarchy

| Alert Category | Trigger Condition | Severity | Recommended Action |
| :--- | :--- | :---: | :--- |
| **Sensor power OFF** | Device or PDU reports power cut | Warning | Inspect local power switch, wiring, and breaker. |
| **Sensor disconnected** | Gateway heartbeat lost | Warning | Check LoRaWAN gateway, signal RSSI, and antenna. |
| **Missing readings** | 2 consecutive missing intervals (10 min) | Warning | Monitor gateway queue; standby for field dispatch. |
| **Extended sensor outage**| 3 or more consecutive missing (15+ min) | **Critical** | Dispatch instrumentation technician immediately. |
| **Sensor malfunction** | Invalid, frozen, or drifting transducer | Warning/Critical | Recalibrate transducer orifice; replace sensor. |
| **Low battery** | Battery level $\le 20.0\%$ | Warning | Schedule battery replacement during next shift. |
| **Sensor recovered** | 2 consecutive valid readings received | Informational | No action required; sensor restored to fleet. |

### Incident Deduplication Mechanism
- Ongoing continuous outages update `last_detected_timestamp`, `missing_duration_minutes`, and `consecutive_missing_count` on the **existing open alert**.
- A sensor offline for 2 hours generates **one continuous incident alert**, preventing alert fatigue.
- Upon 2 consecutive valid readings, the open incident is **automatically moved to `RESOLVED`** and an informational recovery notification is logged.

---

## 6. Layer 1 & Layer 2 Separation (Evidence Engine)

When an event occurs:

1. **If Sensor is OFFLINE or in MAINTENANCE:**
   - Model inference is **suspended**.
   - Output: `layer_2_water_assessment: INSUFFICIENT_SENSOR_DATA`.
   - `leak_detected: False`, `confidence: 0.0`.
   - Prevents missing pressure readings from triggering false leak alerts.
2. **If Sensor is FAULTY (Stuck / Drifting):**
   - Output: `layer_2_water_assessment: SENSOR_FAULT_FLAGGED`.
   - `leak_detected: False`.
   - Dispatches recalibration notice rather than mobilizing an excavation crew.
3. **If Sensors are HEALTHY:**
   - Full ML inference proceeds (`best_leak_model.joblib`).
   - Cross-verifies physical evidence: Flow surge ($Q \uparrow$) must accompany distribution head loss ($P \downarrow$).
   - Legitimate demand spikes (canteen cooking, morning showers) maintain pressure ($P \ge 2.0$ bar) and are tagged `LEGITIMATE_DEMAND_INCREASE`.
   - Real pipe ruptures ($P < 1.2$ bar) trigger `CONFIRMED_LEAK_BURST` with direct plumbing dispatch.

---

## 7. Backend REST API Documentation

Base URL: `http://localhost:8000/api/v1`

### 7.1 Sensor Fleet Management
- **`GET /api/v1/sensors`**
  - Query parameters: `zone_id` (`HOSTEL`, `CANTEEN`, etc.), `health_status` (`HEALTHY`, `OFFLINE`, etc.)
  - Returns array of all 12 sensors with power, connectivity, health, battery %, missing count, and last valid timestamp.
- **`GET /api/v1/sensors/health`**
  - Returns fleet summary counts (Total, Healthy, Offline, Faulty, Maintenance) and zone-by-zone breakdown.
- **`GET /api/v1/sensors/{sensor_id}`**
  - Returns detailed sensor profile, recent 20 readings, and complete incident history.

### 7.2 Alert Management
- **`GET /api/v1/sensors/alerts`**
  - Query parameters: `status` (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`), `severity` (`Critical`, `Warning`), `meter_id`
  - Returns deduplicated list of recorded alert incidents.
- **`GET /api/v1/sensors/alerts/summary`**
  - Returns active critical, warning, and resolved incident counts.
- **`PATCH /api/v1/sensors/alerts/{alert_id}/acknowledge`**
  - Body: `{"user_id": "operator_name", "note": "Technician en route"}`
  - Moves alert status from `OPEN` to `ACKNOWLEDGED`.
- **`PATCH /api/v1/sensors/alerts/{alert_id}/resolve`**
  - Body: `{"user_id": "technician_name", "resolution_note": "Sensor rebooted"}`
  - Manually marks alert `RESOLVED`.

### 7.3 Telemetry Ingestion & Live Inference
- **`POST /api/v1/telemetry/ingest`**
  - Ingests single 5-minute telemetry packet.
  - Returns dual-layer response (`layer_1_sensor_health` + `layer_2_water_intelligence`).

---

## 8. Dashboard User Interface

The frontend dashboard is accessible at `http://localhost:8000/` or `http://localhost:8000/dashboard`:

1. **Fleet KPI Cards:** Real-time counters for Total Sensors, Healthy, Offline, Faulty, and Maintenance.
2. **Sensor Status Table:** Color-coded badges for Health Status, Power Status, Connectivity, and Battery Level with per-sensor inspection modal.
3. **Alert Incident Center:** Live feed of Warning and Critical alerts with one-click **Acknowledge** and **Resolve** controls.
4. **Interactive Hardware Scenario Injector:** Allows triggering power cuts, gateway disconnections, transducer freezes, or maintenance windows with live UI updates.

---

## 9. Steps to Connect Actual IoT Hardware

To transition from simulation to live physical deployment:

1. **Hardware Selection:**
   - Ultrasonic smart flow meter (e.g. Kamstrup flowIQ, TUF-2000M) with RS-485 Modbus RTU or pulse output.
   - Piezoresistive pressure transmitter (4–20mA, 0–10 bar) connected to an industrial IoT edge gateway.
2. **Gateway Configuration:**
   - Configure a LoRaWAN / 4G LTE Gateway (e.g. Milesight UG65, Dragino DLOS8) on the campus private network.
   - Configure gateway packet forwarding via MQTT over TLS.
3. **Payload Decoder:**
   - Map raw binary payload to the `TelemetryIngestRequest` JSON schema.
4. **Backend Ingestion Endpoint:**
   - Subscribe the FastAPI application to the campus MQTT broker topic `campus/water/+/telemetry`.
   - On incoming packet, forward to `sensor_service.process_reading()`.
5. **Hardware Watchdog:**
   - Configure device hardware watchdogs to emit a last-gasp packet with `sensor_power_status = 'OFF'` before brownout.

---

## 10. Simulation Limitations

1. **Gaussian Sensor Drift:** Synthetic sensor drift uses linear and polynomial drift profiles; real-world biofouling exhibits non-linear temperature-dependent resistance.
2. **Synchronized 5-Minute Clocks:** Simulation assumes exact 5-minute ticks; real cellular IoT sensors exhibit jitter ($\pm 15$ seconds) that requires timestamp window aggregation.
3. **Battery Model:** Battery discharge is modeled as a monotonic decay curve; physical LiFePO4 cells experience voltage plateauing followed by steep non-linear drop-off below 3.0V.
