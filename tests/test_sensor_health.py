"""
AquaGuard AI - Unit & Integration Test Suite for Sensor Health Monitoring
Tests all 15 operational scenarios specified in Master Implementation Prompt Section 11.
"""

import pytest
import datetime
import pandas as pd
import numpy as np

from src.sensor_health_service import SensorHealthService, WARNING_MISSING_COUNT, CRITICAL_MISSING_COUNT, RECOVERY_VALID_COUNT
from src.evidence_engine import EvidenceBasedDecisionEngine


@pytest.fixture
def service():
    srv = SensorHealthService()
    srv._init_sensor('M01', zone_id='HOSTEL')
    srv._init_sensor('M02', zone_id='HOSTEL')
    return srv


@pytest.fixture
def evidence():
    return EvidenceBasedDecisionEngine()


# -----------------------------------------------------------------------------
# Test 1: Normal Sensor Operation
# -----------------------------------------------------------------------------
def test_01_normal_sensor_operation(service):
    ts = datetime.datetime(2026, 10, 1, 10, 0, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'CONNECTED',
        'reading_received': 1,
        'sensor_fault_type': 'NONE'
    })
    assert res['health_status'] == 'HEALTHY'
    assert res['consecutive_missing'] == 0
    assert res['consecutive_valid'] == 1
    assert len(res['alerts_triggered']) == 0


# -----------------------------------------------------------------------------
# Test 2: Sensor Powered OFF
# -----------------------------------------------------------------------------
def test_02_sensor_powered_off(service):
    ts = datetime.datetime(2026, 10, 1, 10, 5, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0
    })
    assert res['health_status'] == 'OFFLINE'
    assert res['power_status'] == 'OFF'
    assert res['consecutive_missing'] == 1
    # Triggered "Sensor power OFF" alert
    assert any(a['alert_category'] == 'Sensor power OFF' for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 3: Sensor Disconnected (Gateway Communication Lost)
# -----------------------------------------------------------------------------
def test_03_sensor_disconnected(service):
    ts = datetime.datetime(2026, 10, 1, 10, 5, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0
    })
    assert res['health_status'] == 'OFFLINE'
    assert res['connectivity_status'] == 'DISCONNECTED'
    assert any(a['alert_category'] == 'Sensor disconnected' for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 4: Missing One Reading (Transient Glitch - No Outage Alert)
# -----------------------------------------------------------------------------
def test_04_missing_one_reading_no_outage_alert(service):
    # Valid reading first
    t1 = datetime.datetime(2026, 10, 1, 10, 0, 0)
    service.process_reading({'meter_id': 'M01', 'timestamp': t1, 'reading_received': 1})
    
    # 1 missing reading
    t2 = datetime.datetime(2026, 10, 1, 10, 5, 0)
    res = service.process_reading({'meter_id': 'M01', 'timestamp': t2, 'reading_received': 0})
    assert res['consecutive_missing'] == 1
    # Should NOT trigger missing readings alert (threshold is 2)
    assert not any(a['alert_category'] in ['Missing readings', 'Extended sensor outage'] for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 5: Two Consecutive Missing Readings (Warning Threshold: 10 mins)
# -----------------------------------------------------------------------------
def test_05_two_consecutive_missing_readings_warning(service):
    t1 = datetime.datetime(2026, 10, 1, 10, 5, 0)
    t2 = datetime.datetime(2026, 10, 1, 10, 10, 0)
    service.process_reading({'meter_id': 'M01', 'timestamp': t1, 'reading_received': 0})
    res2 = service.process_reading({'meter_id': 'M01', 'timestamp': t2, 'reading_received': 0})
    
    assert res2['consecutive_missing'] == 2
    assert res2['health_status'] == 'WARNING'
    assert any(a['alert_category'] == 'Missing readings' and a['severity'] == 'Warning' for a in res2['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 6: Three Consecutive Missing Readings (Critical Outage: 15 mins)
# -----------------------------------------------------------------------------
def test_06_three_consecutive_missing_readings_critical(service):
    for i in range(1, 4):
        ts = datetime.datetime(2026, 10, 1, 10, i * 5, 0)
        res = service.process_reading({'meter_id': 'M01', 'timestamp': ts, 'reading_received': 0})
        
    assert res['consecutive_missing'] == 3
    assert res['health_status'] == 'OFFLINE'
    assert any(a['alert_category'] == 'Extended sensor outage' and a['severity'] == 'Critical' for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 7: Sensor Stuck at Same Value
# -----------------------------------------------------------------------------
def test_07_sensor_stuck_fault(service):
    ts = datetime.datetime(2026, 10, 1, 10, 0, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'reading_received': 1,
        'sensor_fault_type': 'SENSOR_STUCK'
    })
    assert res['health_status'] == 'FAULTY'
    assert any(a['alert_category'] == 'Sensor malfunction' and a['severity'] == 'Critical' for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 8: Sensor Drift
# -----------------------------------------------------------------------------
def test_08_sensor_drift_fault(service):
    ts = datetime.datetime(2026, 10, 1, 10, 0, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'reading_received': 1,
        'sensor_fault_type': 'SENSOR_DRIFT'
    })
    assert res['health_status'] == 'FAULTY'
    assert any('SENSOR_DRIFT' in a['alert_message'] for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 9: Sensor Spike
# -----------------------------------------------------------------------------
def test_09_sensor_spike_fault(service):
    ts = datetime.datetime(2026, 10, 1, 10, 0, 0)
    res = service.process_reading({
        'meter_id': 'M01',
        'timestamp': ts,
        'reading_received': 1,
        'sensor_fault_type': 'SENSOR_SPIKE'
    })
    assert res['health_status'] == 'FAULTY'
    assert any(a['alert_category'] == 'Sensor malfunction' and a['severity'] == 'Warning' for a in res['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 10: Planned Maintenance (Suppressed Emergency Alerts)
# -----------------------------------------------------------------------------
def test_10_planned_maintenance(service):
    # Even with 4 missing readings, under maintenance NO critical outage alerts are emitted
    for i in range(1, 5):
        ts = datetime.datetime(2026, 10, 1, 10, i * 5, 0)
        res = service.process_reading({
            'meter_id': 'M01',
            'timestamp': ts,
            'reading_received': 0,
            'maintenance_mode': True
        })
    assert res['health_status'] == 'MAINTENANCE'
    assert len(res['alerts_triggered']) == 0


# -----------------------------------------------------------------------------
# Test 11: Sensor Recovery (Auto-Resolve after 2 Valid Readings)
# -----------------------------------------------------------------------------
def test_11_sensor_recovery(service):
    # Step 1: Outage of 3 missing readings (generates alert)
    for i in range(1, 4):
        ts = datetime.datetime(2026, 10, 1, 10, i * 5, 0)
        service.process_reading({'meter_id': 'M01', 'timestamp': ts, 'reading_received': 0})
    
    # Active alert exists
    assert len(service.active_alerts) > 0

    # Step 2: 1st valid reading received (recovery counter = 1)
    t4 = datetime.datetime(2026, 10, 1, 10, 20, 0)
    res1 = service.process_reading({'meter_id': 'M01', 'timestamp': t4, 'reading_received': 1})
    assert res1['consecutive_valid'] == 1
    assert len(service.active_alerts) > 0 # Still open

    # Step 3: 2nd consecutive valid reading (triggers recovery condition)
    t5 = datetime.datetime(2026, 10, 1, 10, 25, 0)
    res2 = service.process_reading({'meter_id': 'M01', 'timestamp': t5, 'reading_received': 1})
    assert res2['consecutive_valid'] == 2
    assert len(service.active_alerts) == 0 # Outage alerts auto-resolved!
    assert any(a['alert_category'] == 'Sensor recovered' for a in res2['alerts_triggered'])


# -----------------------------------------------------------------------------
# Test 12: Duplicate Alert Prevention
# -----------------------------------------------------------------------------
def test_12_duplicate_alert_prevention(service):
    # Outage continuing for 10 intervals
    total_triggered = []
    for i in range(1, 11):
        ts = datetime.datetime(2026, 10, 1, 10, i * 5, 0)
        res = service.process_reading({'meter_id': 'M01', 'timestamp': ts, 'reading_received': 0})
        total_triggered.extend(res['alerts_triggered'])

    # Verify deduplication: Critical extended outage alert triggered ONCE, not on every subsequent row!
    crit_alerts = [a for a in total_triggered if a['alert_category'] == 'Extended sensor outage']
    assert len(crit_alerts) == 1


# -----------------------------------------------------------------------------
# Test 13: Missing Pressure Data During Leak Inference (Layer 1 + Layer 2 Decoupling)
# -----------------------------------------------------------------------------
def test_13_missing_pressure_during_leak_inference(evidence):
    sensor_info = {
        'health_status': 'OFFLINE',
        'power_status': 'ON',
        'connectivity_status': 'DISCONNECTED',
        'reading_received': 0
    }
    telemetry = {
        'meter_id': 'M01',
        'inlet_flow_lpm': 45.0, # High flow
        'pressure_bar': None    # Missing pressure!
    }
    res = evidence.evaluate_telemetry(sensor_info, telemetry)
    # MUST return INSUFFICIENT_SENSOR_DATA, never a false leak!
    assert res['layer_2_water_assessment'] == 'INSUFFICIENT_SENSOR_DATA'
    assert res['leak_detected'] is False
    assert res['alert_action'] == 'DISPATCH_INSTRUMENTATION_TECHNICIAN'


# -----------------------------------------------------------------------------
# Test 14: Missing Flow Data During Anomaly Detection
# -----------------------------------------------------------------------------
def test_14_missing_flow_data_during_anomaly(evidence):
    sensor_info = {
        'health_status': 'OFFLINE',
        'power_status': 'OFF',
        'connectivity_status': 'DISCONNECTED',
        'reading_received': 0
    }
    telemetry = {
        'meter_id': 'M02',
        'inlet_flow_lpm': None,
        'pressure_bar': 2.2,
        'interval_consumption_liters': None
    }
    res = evidence.evaluate_telemetry(sensor_info, telemetry)
    assert res['layer_2_water_assessment'] == 'INSUFFICIENT_SENSOR_DATA'
    assert res['anomaly_detected'] is False


# -----------------------------------------------------------------------------
# Test 15: Simultaneous Outage of Multiple Sensors
# -----------------------------------------------------------------------------
def test_15_simultaneous_multi_sensor_outage(service):
    # Both M01 and M02 experience power outages simultaneously
    ts = datetime.datetime(2026, 10, 1, 10, 15, 0)
    for i in range(1, 4):
        t = ts + datetime.timedelta(minutes=i*5)
        service.process_reading({'meter_id': 'M01', 'timestamp': t, 'reading_received': 0, 'sensor_power_status': 'OFF'})
        service.process_reading({'meter_id': 'M02', 'timestamp': t, 'reading_received': 0, 'sensor_power_status': 'OFF'})

    s1 = service.sensor_states['M01']
    s2 = service.sensor_states['M02']
    assert s1['health_status'] == 'OFFLINE'
    assert s2['health_status'] == 'OFFLINE'
    # Distinct alerts for both meters
    m1_alerts = [a for a in service.alert_history if a['meter_id'] == 'M01']
    m2_alerts = [a for a in service.alert_history if a['meter_id'] == 'M02']
    assert len(m1_alerts) > 0
    assert len(m2_alerts) > 0
