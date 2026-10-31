"""
AquaGuard AI - Sensor Health Monitoring & Missing Data Alert API
FastAPI Backend providing REST endpoints for Sensor Registry, Health Tracking,
Alert Management, and Evidence-Based Leak Detection.
"""

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import datetime
import os
import uuid

from src.database import SessionLocal, SensorModel, SensorReadingModel, SensorAlertModel, init_db
from src.sensor_health_service import SensorHealthService
from src.evidence_engine import EvidenceBasedDecisionEngine

init_db()

app = FastAPI(
    title="AquaGuard AI — Sensor Health Monitoring & Alert System",
    description="Dual-Layer IoT Intelligence: Layer 1 Sensor Telemetry & Layer 2 Water Resilience",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared in-memory service instances
sensor_service = SensorHealthService()
evidence_engine = EvidenceBasedDecisionEngine()

# Initialize sensor service with 12 meters from DB
db_session = SessionLocal()
existing_sensors = db_session.query(SensorModel).all()
for s in existing_sensors:
    sensor_service._init_sensor(s.meter_id, s.zone_id, s.campus_id, s.sensor_type)
    state = sensor_service.sensor_states[s.meter_id]
    state['health_status'] = s.health_status
    state['power_status'] = s.power_status
    state['connectivity_status'] = s.connectivity_status
    state['battery_pct'] = s.battery_percentage
    state['last_valid_timestamp'] = s.last_reading_timestamp
    state['maintenance_mode'] = (s.maintenance_status == "UNDER_MAINTENANCE")
db_session.close()

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------

class SensorAcknowledgeRequest(BaseModel):
    user_id: str = Field(default="facility_operator", description="Operator acknowledging alert")
    note: Optional[str] = Field(default=None, description="Optional acknowledgement note")

class SensorResolveRequest(BaseModel):
    user_id: str = Field(default="maintenance_admin", description="Technician resolving incident")
    resolution_note: str = Field(default="Transducer inspected and restored to service.")

class TelemetryIngestRequest(BaseModel):
    meter_id: str
    timestamp: Optional[str] = None
    zone_type: Optional[str] = "HOSTEL"
    hour: Optional[int] = 12
    occupancy: Optional[int] = 0
    scheduled_activity: Optional[int] = 0
    inlet_flow_lpm: Optional[float] = None
    pressure_bar: Optional[float] = None
    tank_level_pct: Optional[float] = 75.0
    previous_1h_avg_flow_lpm: Optional[float] = None
    previous_1h_avg_pressure_bar: Optional[float] = None
    flow_change_lpm: Optional[float] = 0.0
    pressure_change_bar: Optional[float] = 0.0
    sensor_power_status: Optional[str] = "ON"
    sensor_connectivity_status: Optional[str] = "CONNECTED"
    reading_received: Optional[int] = 1
    sensor_battery_pct: Optional[float] = 95.0
    sensor_fault_type: Optional[str] = "NONE"
    maintenance_mode: Optional[bool] = False

# -----------------------------------------------------------------------------
# DEPENDENCY
# -----------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------------------------------------------------------
# REST ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/v1/system/status")
def get_system_status():
    """System health and operational mode."""
    return {
        'status': 'OPERATIONAL',
        'simulation_mode': True,
        'environment': 'AquaGuard AI Smart Campus Pilot',
        'active_monitors': 12,
        'monitoring_interval_minutes': 5,
        'current_timestamp': datetime.datetime.now().isoformat(),
        'dual_engine_active': True
    }


@app.get("/api/v1/sensors")
def get_all_sensors(
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    health_status: Optional[str] = Query(None, description="Filter by health status"),
    db=Depends(get_db)
):
    """List all sensors with their latest operational status."""
    query = db.query(SensorModel)
    if zone_id:
        query = query.filter(SensorModel.zone_id == zone_id.upper())
    if health_status:
        query = query.filter(SensorModel.health_status == health_status.upper())

    sensors = query.all()
    # Enrich with live service runtime counters
    results = []
    for s in sensors:
        d = s.to_dict()
        runtime_state = sensor_service.sensor_states.get(s.meter_id, {})
        d['consecutive_missing'] = runtime_state.get('consecutive_missing', 0)
        d['consecutive_valid'] = runtime_state.get('consecutive_valid', 0)
        d['active_fault'] = runtime_state.get('active_fault', 'NONE')
        results.append(d)
    return results


@app.get("/api/v1/sensors/health")
def get_sensors_health_summary(db=Depends(get_db)):
    """Summary overview of sensor health across the campus."""
    summary = sensor_service.get_summary()
    
    # Zone-wise health breakdown
    sensors = db.query(SensorModel).all()
    zone_breakdown = {}
    for s in sensors:
        z = s.zone_id
        if z not in zone_breakdown:
            zone_breakdown[z] = {'total': 0, 'healthy': 0, 'offline': 0, 'faulty': 0, 'warning': 0, 'maintenance': 0}
        zone_breakdown[z]['total'] += 1
        h_key = s.health_status.lower()
        if h_key in zone_breakdown[z]:
            zone_breakdown[z][h_key] += 1

    summary['zone_breakdown'] = zone_breakdown
    summary['simulation_mode_label'] = "SIMULATION ENVIRONMENT (Realistic Hardware SCADA Emulation)"
    return summary


@app.get("/api/v1/sensors/alerts/summary")
def get_sensor_alerts_summary():
    """Summary counts of sensor alerts by status and severity."""
    all_alerts = sensor_service.alert_history
    return {
        'total_recorded_alerts': len(all_alerts),
        'open_alerts': sum(1 for a in all_alerts if a['alert_status'] == 'OPEN'),
        'acknowledged_alerts': sum(1 for a in all_alerts if a['alert_status'] == 'ACKNOWLEDGED'),
        'resolved_alerts': sum(1 for a in all_alerts if a['alert_status'] == 'RESOLVED'),
        'critical_active': sum(1 for a in all_alerts if a['severity'] == 'Critical' and a['alert_status'] in ['OPEN', 'ACKNOWLEDGED']),
        'warning_active': sum(1 for a in all_alerts if a['severity'] == 'Warning' and a['alert_status'] in ['OPEN', 'ACKNOWLEDGED']),
        'informational_active': sum(1 for a in all_alerts if a['severity'] == 'Informational' and a['alert_status'] in ['OPEN', 'ACKNOWLEDGED'])
    }


@app.get("/api/v1/sensors/alerts")
def get_sensor_alerts(
    status: Optional[str] = Query(None, description="Filter by status: OPEN, ACKNOWLEDGED, RESOLVED"),
    severity: Optional[str] = Query(None, description="Filter by severity: Critical, Warning, Informational"),
    meter_id: Optional[str] = Query(None, description="Filter by meter ID")
):
    """Query sensor alerts with deduplication history."""
    alerts = sensor_service.alert_history
    if status:
        alerts = [a for a in alerts if a['alert_status'].upper() == status.upper()]
    if severity:
        alerts = [a for a in alerts if a['severity'].upper() == severity.upper()]
    if meter_id:
        alerts = [a for a in alerts if a['meter_id'].upper() == meter_id.upper()]

    # Sort most recent first
    return sorted(alerts, key=lambda x: x['last_detected_timestamp'], reverse=True)


@app.patch("/api/v1/sensors/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, payload: SensorAcknowledgeRequest, db=Depends(get_db)):
    """Acknowledge an open sensor alert."""
    alert = sensor_service.acknowledge_alert(alert_id, user_id=payload.user_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    # Also update DB model if present
    db_alert = db.query(SensorAlertModel).filter_by(alert_id=alert_id).first()
    if db_alert:
        db_alert.alert_status = "ACKNOWLEDGED"
        db_alert.acknowledged_by = payload.user_id
        db.commit()

    return {'message': 'Alert acknowledged successfully', 'alert': alert}


@app.patch("/api/v1/sensors/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, payload: SensorResolveRequest, db=Depends(get_db)):
    """Mark an alert manually resolved by a technician."""
    alert = sensor_service.resolve_alert(alert_id, note=payload.resolution_note)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    db_alert = db.query(SensorAlertModel).filter_by(alert_id=alert_id).first()
    if db_alert:
        db_alert.alert_status = "RESOLVED"
        db_alert.resolved_at = datetime.datetime.utcnow()
        db.commit()

    return {'message': 'Alert resolved successfully', 'alert': alert}


@app.get("/api/v1/sensors/{sensor_id}")
def get_sensor_detail(sensor_id: str, db=Depends(get_db)):
    """Detailed profile of a single sensor including reading history and alerts."""
    # Allow querying by either sensor_id (e.g. SENSOR_M01) or meter_id (e.g. M01)
    sensor = db.query(SensorModel).filter(
        (SensorModel.sensor_id == sensor_id) | (SensorModel.meter_id == sensor_id)
    ).first()

    if not sensor:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found.")

    meter_id = sensor.meter_id
    runtime_state = sensor_service.sensor_states.get(meter_id, {})

    # Fetch recent readings
    readings = db.query(SensorReadingModel).filter_by(sensor_id=sensor.sensor_id).order_by(SensorReadingModel.timestamp.desc()).limit(20).all()
    # Fetch alerts for this sensor
    alerts = [a for a in sensor_service.alert_history if a['meter_id'] == meter_id or a['sensor_id'] == sensor.sensor_id]

    detail = sensor.to_dict()
    detail['consecutive_missing'] = runtime_state.get('consecutive_missing', 0)
    detail['consecutive_valid'] = runtime_state.get('consecutive_valid', 0)
    detail['active_fault'] = runtime_state.get('active_fault', 'NONE')
    detail['recent_readings'] = [r.to_dict() for r in readings]
    detail['alert_history'] = sorted(alerts, key=lambda x: x['first_detected_timestamp'], reverse=True)
    return detail


@app.post("/api/v1/telemetry/ingest")
def ingest_telemetry_reading(payload: TelemetryIngestRequest, db=Depends(get_db)):
    """
    Ingest a 5-minute telemetry packet.
    Executes:
    1. Layer 1 Sensor Health Monitoring (State, Missing Data, Incident Alerts).
    2. Layer 2 Evidence-Based Water Intelligence (ML Leak Classification + Evidence Audit).
    """
    ts_now = payload.timestamp or datetime.datetime.utcnow().isoformat()
    raw_dict = payload.dict()
    raw_dict['timestamp'] = ts_now

    # 1. Process Layer 1 Sensor Health
    sensor_result = sensor_service.process_reading(raw_dict)

    # Update database sensor record
    sensor = db.query(SensorModel).filter_by(meter_id=payload.meter_id).first()
    if sensor:
        sensor.power_status = sensor_result['power_status']
        sensor.connectivity_status = sensor_result['connectivity_status']
        sensor.health_status = sensor_result['health_status']
        sensor.battery_percentage = sensor_result['battery_pct']
        if sensor_result['health_status'] != 'MAINTENANCE':
            sensor.maintenance_status = "OPERATIONAL"
        else:
            sensor.maintenance_status = "UNDER_MAINTENANCE"
        if sensor_result['classification'] == 'HEALTHY':
            sensor.last_reading_timestamp = datetime.datetime.fromisoformat(ts_now)
        db.commit()

        # Log reading
        reading_entry = SensorReadingModel(
            reading_id=f"RDG_{uuid.uuid4().hex[:8].upper()}",
            sensor_id=sensor.sensor_id,
            timestamp=datetime.datetime.fromisoformat(ts_now),
            measured_flow_lpm=payload.inlet_flow_lpm,
            measured_pressure_bar=payload.pressure_bar,
            reading_status="RECEIVED" if payload.reading_received == 1 else "MISSING",
            is_valid=(payload.reading_received == 1 and sensor_result['health_status'] in ['HEALTHY', 'WARNING'])
        )
        db.add(reading_entry)
        db.commit()

    # 2. Process Layer 2 Evidence Engine
    evidence_result = evidence_engine.evaluate_telemetry(sensor_result, raw_dict)

    # Persist any generated alerts into DB
    for a in sensor_result['alerts_triggered']:
        db_alert = SensorAlertModel(
            alert_id=a['alert_id'],
            sensor_id=a['sensor_id'],
            zone_id=a['zone_id'],
            alert_type=a['alert_category'],
            severity=a['severity'],
            message=a['alert_message'],
            recommended_action=a['recommended_action'],
            first_detected_at=datetime.datetime.fromisoformat(a['first_detected_timestamp']),
            last_detected_at=datetime.datetime.fromisoformat(a['last_detected_timestamp']),
            missing_duration_minutes=a['missing_duration_minutes'],
            alert_status=a['alert_status']
        )
        db.add(db_alert)
    db.commit()

    return {
        'timestamp': ts_now,
        'meter_id': payload.meter_id,
        'layer_1_sensor_health': sensor_result,
        'layer_2_water_intelligence': evidence_result
    }


# -----------------------------------------------------------------------------
# FRONTEND STATIC FILES & DASHBOARD ROUTE
# -----------------------------------------------------------------------------

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def serve_dashboard():
    dashboard_file = os.path.join(static_dir, "index.html")
    if os.path.exists(dashboard_file):
        with open(dashboard_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AquaGuard AI Dashboard loading...</h1>"
