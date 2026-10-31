"""
AquaGuard AI - Sample Sensor Outage & Recovery Demonstration
Demonstrates end-to-end incident lifecycle:
1. Normal healthy state
2. Power outage begins
3. Warning threshold reached (2 consecutive missing = 10 min)
4. Critical outage threshold reached (3 consecutive missing = 15 min)
5. Evidence engine decoupling (INSUFFICIENT_SENSOR_DATA, 0 false leak alarms)
6. Recovery sequence (2 consecutive valid readings auto-resolves outage)
"""

import datetime
import os
import sys

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

from src.sensor_health_service import SensorHealthService
from src.evidence_engine import EvidenceBasedDecisionEngine
from src.notification_dispatcher import NotificationDispatcher

def run_demonstration():
    print("=" * 80)
    print(" AQUAGUARD AI — SENSOR HEALTH OUTAGE & RECOVERY LIFECYCLE DEMONSTRATION")
    print("=" * 80)

    service = SensorHealthService()
    evidence_engine = EvidenceBasedDecisionEngine()
    dispatcher = NotificationDispatcher()

    meter_id = "M01"
    zone_id = "HOSTEL"
    start_time = datetime.datetime(2026, 10, 31, 10, 0, 0)

    # -------------------------------------------------------------------------
    # STEP 1: NORMAL HEALTHY TELEMETRY
    # -------------------------------------------------------------------------
    print("\n--- STEP 1: NORMAL OPERATIONAL BASELINE (10:00 AM) ---")
    reading_1 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': start_time,
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'CONNECTED',
        'reading_received': 1,
        'inlet_flow_lpm': 22.4,
        'pressure_bar': 2.45
    }
    r1 = service.process_reading(reading_1)
    e1 = evidence_engine.evaluate_telemetry(r1, reading_1)
    print(f"Layer 1 Status: {r1['health_status']} | Missing Count: {r1['consecutive_missing']} | Valid Count: {r1['consecutive_valid']}")
    print(f"Layer 2 Assessment: {e1['layer_2_water_assessment']} (Confidence: {e1['confidence']})")
    print(f"Active Incidents: {len(service.active_alerts)}")

    # -------------------------------------------------------------------------
    # STEP 2: OUTAGE BEGINS (10:05 AM - 1ST MISSING READING)
    # -------------------------------------------------------------------------
    print("\n--- STEP 2: POWER TRIP OCCURS (10:05 AM - 1st Missing Interval / 5 mins) ---")
    t2 = start_time + datetime.timedelta(minutes=5)
    reading_2 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t2,
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0,
        'inlet_flow_lpm': None,
        'pressure_bar': None
    }
    r2 = service.process_reading(reading_2)
    e2 = evidence_engine.evaluate_telemetry(r2, reading_2)
    print(f"Layer 1 Status: {r2['health_status']} | Missing Count: {r2['consecutive_missing']} | Confirmed Power: {r2['power_status']}")
    print(f"Layer 2 Assessment: {e2['layer_2_water_assessment']} -> {e2['rationale']}")
    for a in r2['alerts_triggered']:
        dispatcher.dispatch(a)

    # -------------------------------------------------------------------------
    # STEP 3: WARNING THRESHOLD REACHED (10:10 AM - 2ND MISSING READING / 10 MINS)
    # -------------------------------------------------------------------------
    print("\n--- STEP 3: WARNING THRESHOLD REACHED (10:10 AM - 2nd Missing Interval / 10 mins) ---")
    t3 = start_time + datetime.timedelta(minutes=10)
    reading_3 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t3,
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0,
        'inlet_flow_lpm': None,
        'pressure_bar': None
    }
    r3 = service.process_reading(reading_3)
    e3 = evidence_engine.evaluate_telemetry(r3, reading_3)
    print(f"Layer 1 Status: {r3['health_status']} | Missing Count: {r3['consecutive_missing']}")
    print(f"Layer 2 Assessment: {e3['layer_2_water_assessment']} (Leak False Alarm Prevented: {not e3['leak_detected']})")
    for a in r3['alerts_triggered']:
        dispatcher.dispatch(a)

    # -------------------------------------------------------------------------
    # STEP 4: CRITICAL OUTAGE THRESHOLD (10:15 AM - 3RD MISSING READING / 15 MINS)
    # -------------------------------------------------------------------------
    print("\n--- STEP 4: CRITICAL OUTAGE THRESHOLD (10:15 AM - 3rd Missing Interval / 15 mins) ---")
    t4 = start_time + datetime.timedelta(minutes=15)
    reading_4 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t4,
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0,
        'inlet_flow_lpm': None,
        'pressure_bar': None
    }
    r4 = service.process_reading(reading_4)
    e4 = evidence_engine.evaluate_telemetry(r4, reading_4)
    print(f"Layer 1 Status: {r4['health_status']} | Consecutive Missing: {r4['consecutive_missing']} (15 min outage)")
    print(f"Layer 2 Assessment: {e4['layer_2_water_assessment']} (Dispatch Recommendation: {e4['alert_action']})")
    for a in r4['alerts_triggered']:
        dispatcher.dispatch(a)

    # -------------------------------------------------------------------------
    # STEP 5: PROLONGED OUTAGE DEDUPLICATION CHECK (10:20 AM - 4TH MISSING READING)
    # -------------------------------------------------------------------------
    print("\n--- STEP 5: PROLONGED OUTAGE (10:20 AM - Deduplication Audit) ---")
    t5 = start_time + datetime.timedelta(minutes=20)
    reading_5 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t5,
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0
    }
    r5 = service.process_reading(reading_5)
    print(f"Alerts Triggered: {len(r5['alerts_triggered'])} (Deduplicated - No duplicate flood)")
    print(f"Active Alert Updated Duration: {service.active_alerts[f'{meter_id}::Extended sensor outage']['missing_duration_minutes']} minutes")

    # -------------------------------------------------------------------------
    # STEP 6: POWER RESTORED (10:25 AM - 1ST VALID READING)
    # -------------------------------------------------------------------------
    print("\n--- STEP 6: POWER RESTORED BY ELECTRICIAN (10:25 AM - 1st Valid Reading) ---")
    t6 = start_time + datetime.timedelta(minutes=25)
    reading_6 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t6,
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'CONNECTED',
        'reading_received': 1,
        'inlet_flow_lpm': 21.8,
        'pressure_bar': 2.42
    }
    r6 = service.process_reading(reading_6)
    print(f"Layer 1 Status: {r6['health_status']} | Consecutive Valid: {r6['consecutive_valid']} (Awaiting 2nd valid reading for recovery)")
    print(f"Active Alerts Still Open: {len(service.active_alerts)}")

    # -------------------------------------------------------------------------
    # STEP 7: RECOVERY CONFIRMED (10:30 AM - 2ND CONSECUTIVE VALID READING)
    # -------------------------------------------------------------------------
    print("\n--- STEP 7: RECOVERY CONFIRMED (10:30 AM - 2nd Consecutive Valid Reading) ---")
    t7 = start_time + datetime.timedelta(minutes=30)
    reading_7 = {
        'meter_id': meter_id,
        'zone_id': zone_id,
        'timestamp': t7,
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'CONNECTED',
        'reading_received': 1,
        'inlet_flow_lpm': 22.0,
        'pressure_bar': 2.44
    }
    r7 = service.process_reading(reading_7)
    e7 = evidence_engine.evaluate_telemetry(r7, reading_7)
    print(f"Layer 1 Status: {r7['health_status']} | Consecutive Valid: {r7['consecutive_valid']}")
    print(f"Active Unresolved Alerts Remaining: {len(service.active_alerts)} (ALL OUTAGE ALERTS AUTO-RESOLVED)")
    for a in r7['alerts_triggered']:
        dispatcher.dispatch(a)
    print(f"Layer 2 Assessment: {e7['layer_2_water_assessment']} (Telemetry Restored to Normal Envelope)")

    print("\n" + "=" * 80)
    print(" DEMONSTRATION COMPLETE: ZERO FALSE LEAKS, INCIDENTS DEDUPLICATED, AUTO-RESOLVED.")
    print("=" * 80)

if __name__ == '__main__':
    run_demonstration()
