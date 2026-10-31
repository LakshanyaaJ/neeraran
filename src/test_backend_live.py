"""
AquaGuard AI - Quick Live Backend Verification Script
Verifies FastAPI endpoints using TestClient.
"""

import os
import sys

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

from fastapi.testclient import TestClient
from src.backend_app import app

client = TestClient(app)

def test_endpoints():
    print("Testing /api/v1/system/status...")
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    print("  System status response:", res.json())

    print("\nTesting /api/v1/sensors/health...")
    res = client.get("/api/v1/sensors/health")
    assert res.status_code == 200
    data = res.json()
    print("  Health summary:", data)
    assert data['total_sensors'] == 12

    print("\nTesting /api/v1/sensors...")
    res = client.get("/api/v1/sensors")
    assert res.status_code == 200
    sensors = res.json()
    print(f"  Retrieved {len(sensors)} sensors.")
    assert len(sensors) == 12

    print("\nTesting Telemetry Ingest (Normal Reading)...")
    ingest_payload = {
        'meter_id': 'M01',
        'sensor_power_status': 'ON',
        'sensor_connectivity_status': 'CONNECTED',
        'reading_received': 1,
        'inlet_flow_lpm': 22.0,
        'pressure_bar': 2.45,
        'hour': 12,
        'occupancy': 15
    }
    res = client.post("/api/v1/telemetry/ingest", json=ingest_payload)
    assert res.status_code == 200
    res_data = res.json()
    print("  Telemetry Ingest Result:")
    print("    Layer 1:", res_data['layer_1_sensor_health']['health_status'])
    print("    Layer 2:", res_data['layer_2_water_intelligence']['layer_2_water_assessment'])

    print("\nTesting Telemetry Ingest (Missing Reading Outage)...")
    outage_payload = {
        'meter_id': 'M02',
        'sensor_power_status': 'OFF',
        'sensor_connectivity_status': 'DISCONNECTED',
        'reading_received': 0,
        'inlet_flow_lpm': None,
        'pressure_bar': None
    }
    # Ingest 3 missing readings
    for i in range(3):
        res = client.post("/api/v1/telemetry/ingest", json=outage_payload)
    assert res.status_code == 200
    res_data = res.json()
    print("  3rd Missing Reading Ingest Result:")
    print("    Layer 1:", res_data['layer_1_sensor_health']['health_status'])
    print("    Layer 2:", res_data['layer_2_water_intelligence']['layer_2_water_assessment'])
    assert res_data['layer_2_water_intelligence']['layer_2_water_assessment'] == 'INSUFFICIENT_SENSOR_DATA'

    print("\nTesting /api/v1/sensors/alerts...")
    res = client.get("/api/v1/sensors/alerts")
    assert res.status_code == 200
    alerts = res.json()
    print(f"  Alerts count: {len(alerts)}")
    assert len(alerts) > 0

    alert_id = alerts[0]['alert_id']
    print(f"\nTesting Alert Acknowledgement for {alert_id}...")
    ack_res = client.patch(f"/api/v1/sensors/alerts/{alert_id}/acknowledge", json={'user_id': 'lead_operator'})
    assert ack_res.status_code == 200
    print("  Ack response:", ack_res.json()['alert']['alert_status'])

    print("\nTesting Dashboard Route GET /...")
    dash_res = client.get("/")
    assert dash_res.status_code == 200
    assert "AquaGuard" in dash_res.text
    print("  Dashboard HTML served successfully (length:", len(dash_res.text), "bytes)")

    print("\nALL BACKEND VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == '__main__':
    test_endpoints()
