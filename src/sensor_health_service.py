"""
AquaGuard AI - Sensor Health Monitoring and Missing Data Alert System (Layer 1)
Tracks device status, detects missing readings, differentiates confirmed OFF vs inferred OFFLINE,
deduplicates alerts per outage incident, and handles auto-recovery.
"""

from typing import Dict, Any, List, Optional
import datetime
import uuid

# Configurable Thresholds
EXPECTED_INTERVAL_MINUTES = 5.0
WARNING_MISSING_COUNT = 2       # 10 minutes
CRITICAL_MISSING_COUNT = 3      # 15 minutes
RECOVERY_VALID_COUNT = 2        # 2 consecutive valid readings to recover
LOW_BATTERY_THRESHOLD = 20.0    # %


class SensorHealthService:
    def __init__(self):
        # Per-sensor runtime state
        self.sensor_states: Dict[str, Dict[str, Any]] = {}
        # Active (open) alerts indexed by (meter_id, alert_category) for incident deduplication
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        # Full historical log of all alerts (OPEN, ACKNOWLEDGED, RESOLVED)
        self.alert_history: List[Dict[str, Any]] = []

    def _init_sensor(self, meter_id: str, zone_id: str = "UNKNOWN", campus_id: str = "CAMPUS_01", sensor_type: str = "FLOW_PRESSURE_METER"):
        if meter_id not in self.sensor_states:
            self.sensor_states[meter_id] = {
                'sensor_id': f"SENSOR_{meter_id}",
                'meter_id': meter_id,
                'campus_id': campus_id,
                'zone_id': zone_id,
                'sensor_type': sensor_type,
                'power_status': 'ON',
                'connectivity_status': 'CONNECTED',
                'health_status': 'HEALTHY',
                'consecutive_missing': 0,
                'consecutive_valid': 0,
                'last_valid_timestamp': None,
                'last_seen_timestamp': None,
                'battery_pct': 100.0,
                'maintenance_mode': False,
                'active_fault': 'NONE'
            }

    def process_reading(self, reading_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a 5-minute incoming reading packet or polling heartbeat.
        reading_data keys:
            meter_id, timestamp, zone_id (optional), campus_id (optional),
            sensor_power_status (optional), sensor_connectivity_status (optional),
            reading_received (1 or 0), sensor_battery_pct (optional),
            sensor_fault_type (optional), maintenance_mode (bool, optional),
            measured_flow (optional), measured_pressure (optional)
        """
        meter_id = reading_data['meter_id']
        ts = pd_timestamp = reading_data['timestamp']
        if isinstance(ts, str):
            ts = datetime.datetime.fromisoformat(ts)

        zone_id = reading_data.get('zone_id', 'UNKNOWN')
        campus_id = reading_data.get('campus_id', 'CAMPUS_01')
        self._init_sensor(meter_id, zone_id, campus_id)
        state = self.sensor_states[meter_id]
        if zone_id != 'UNKNOWN':
            state['zone_id'] = zone_id

        # Device reported inputs (or inferred defaults)
        power_status = reading_data.get('sensor_power_status', 'ON')
        conn_status = reading_data.get('sensor_connectivity_status', 'CONNECTED')
        reading_received = int(reading_data.get('reading_received', 1))
        batt_pct = float(reading_data.get('sensor_battery_pct', state['battery_pct']))
        fault_type = reading_data.get('sensor_fault_type', 'NONE')
        maintenance_mode = bool(reading_data.get('maintenance_mode', reading_data.get('sensor_health_status') == 'MAINTENANCE'))

        state['battery_pct'] = batt_pct
        state['last_seen_timestamp'] = ts
        state['maintenance_mode'] = maintenance_mode
        state['active_fault'] = fault_type

        # Inferred Offline Detection:
        # Check elapsed time since last seen if packet was received vs polling cycle
        if state['last_valid_timestamp'] is not None:
            time_since_valid = (ts - state['last_valid_timestamp']).total_seconds() / 60.0
        else:
            time_since_valid = 0.0

        # Operational Classification Logic (Section 4)
        if maintenance_mode:
            classification = "MAINTENANCE"
            state['power_status'] = 'OFF'
            state['connectivity_status'] = 'DISCONNECTED'
            state['health_status'] = 'MAINTENANCE'
            state['consecutive_valid'] = 0
            state['consecutive_missing'] += 1

        elif power_status == 'OFF':
            classification = "POWER_OFF"
            state['power_status'] = 'OFF'
            state['connectivity_status'] = 'DISCONNECTED'
            state['health_status'] = 'OFFLINE'
            state['consecutive_valid'] = 0
            state['consecutive_missing'] += 1

        elif conn_status == 'DISCONNECTED':
            classification = "COMMUNICATION_FAILURE"
            state['power_status'] = 'ON'
            state['connectivity_status'] = 'DISCONNECTED'
            state['health_status'] = 'OFFLINE'
            state['consecutive_valid'] = 0
            state['consecutive_missing'] += 1

        elif reading_received == 0:
            classification = "MISSING_READING"
            state['consecutive_valid'] = 0
            state['consecutive_missing'] += 1
            state['power_status'] = 'ON'
            # Distinguish confirmed OFF vs inferred OFFLINE
            state['connectivity_status'] = 'DISCONNECTED' if state['consecutive_missing'] >= WARNING_MISSING_COUNT else 'CONNECTED'
            state['health_status'] = 'OFFLINE' if state['consecutive_missing'] >= CRITICAL_MISSING_COUNT else 'WARNING'

        elif fault_type not in ['NONE', None, '']:
            classification = "SENSOR_FAULT"
            state['power_status'] = 'ON'
            state['connectivity_status'] = 'CONNECTED'
            state['health_status'] = 'FAULTY'
            state['consecutive_valid'] = 0
            state['consecutive_missing'] = 0
            state['last_valid_timestamp'] = ts

        else:
            classification = "HEALTHY"
            state['power_status'] = 'ON'
            state['connectivity_status'] = 'CONNECTED'
            state['health_status'] = 'WARNING' if batt_pct <= LOW_BATTERY_THRESHOLD else 'HEALTHY'
            state['consecutive_valid'] += 1
            state['consecutive_missing'] = 0
            state['last_valid_timestamp'] = ts

        # Alert evaluation & lifecycle management
        alerts_generated = self._evaluate_alerts(meter_id, ts, classification)

        return {
            'meter_id': meter_id,
            'timestamp': ts.isoformat(),
            'classification': classification,
            'health_status': state['health_status'],
            'power_status': state['power_status'],
            'connectivity_status': state['connectivity_status'],
            'consecutive_missing': state['consecutive_missing'],
            'consecutive_valid': state['consecutive_valid'],
            'battery_pct': state['battery_pct'],
            'alerts_triggered': alerts_generated
        }

    def _evaluate_alerts(self, meter_id: str, ts: datetime.datetime, classification: str) -> List[Dict[str, Any]]:
        state = self.sensor_states[meter_id]
        alerts_triggered = []

        # Planned maintenance does NOT trigger emergency outage alerts
        if state['maintenance_mode']:
            # Auto-resolve any prior open outage alert under maintenance
            self._resolve_sensor_alerts(meter_id, ts, "Incident resolved: Sensor placed under scheduled maintenance.")
            return []

        # 1. Recovery Check: Sensor sends valid readings for RECOVERY_VALID_COUNT intervals
        if state['consecutive_valid'] >= RECOVERY_VALID_COUNT:
            resolved_count = self._resolve_sensor_alerts(meter_id, ts, f"Sensor recovered: {state['consecutive_valid']} consecutive valid readings received.")
            if resolved_count > 0:
                rec_alert = self._create_alert(
                    meter_id=meter_id,
                    alert_category="Sensor recovered",
                    severity="Informational",
                    first_detected=ts,
                    ts=ts,
                    message=f"INFO: Sensor {meter_id} in {state['zone_id']} Zone recovered and has resumed normal telemetry transmission.",
                    recommended_action="No action required. Sensor restored to normal operational monitoring.",
                    status="RESOLVED"
                )
                alerts_triggered.append(rec_alert)
            return alerts_triggered

        # 2. Critical Outage: 3 or more consecutive missing intervals (15+ min)
        if state['consecutive_missing'] >= CRITICAL_MISSING_COUNT:
            missing_mins = state['consecutive_missing'] * EXPECTED_INTERVAL_MINUTES
            last_ts_str = state['last_valid_timestamp'].strftime('%Y-%m-%d %I:%M %p') if state['last_valid_timestamp'] else "Unknown"
            
            # Escalation or creation of critical outage alert
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Extended sensor outage",
                severity="Critical",
                ts=ts,
                missing_mins=missing_mins,
                missing_count=state['consecutive_missing'],
                message=f"CRITICAL: Sensor {meter_id} in {state['zone_id']} Zone has not transmitted readings for {int(missing_mins)} minutes. The last valid reading was received at {last_ts_str}.",
                recommended_action="Dispatch instrument technician. Check power supply, wiring, gateway connectivity, and physical sensor operation."
            )
            if alert:
                alerts_triggered.append(alert)

        # 3. Warning Outage: Exactly 2 consecutive missing intervals (10 min)
        elif state['consecutive_missing'] == WARNING_MISSING_COUNT:
            missing_mins = state['consecutive_missing'] * EXPECTED_INTERVAL_MINUTES
            last_ts_str = state['last_valid_timestamp'].strftime('%Y-%m-%d %I:%M %p') if state['last_valid_timestamp'] else "Unknown"
            
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Missing readings",
                severity="Warning",
                ts=ts,
                missing_mins=missing_mins,
                missing_count=state['consecutive_missing'],
                message=f"WARNING: Sensor {meter_id} in {state['zone_id']} Zone missed {state['consecutive_missing']} consecutive readings (10 minutes). Last valid reading at {last_ts_str}.",
                recommended_action="Monitor gateway heartbeat. Prepare field check if transmission is not restored within next 5 minutes."
            )
            if alert:
                alerts_triggered.append(alert)

        # 4. Device reports Confirmed Power OFF
        if state['power_status'] == 'OFF' and not state['maintenance_mode']:
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Sensor power OFF",
                severity="Warning",
                ts=ts,
                missing_mins=state['consecutive_missing'] * EXPECTED_INTERVAL_MINUTES,
                missing_count=state['consecutive_missing'],
                message=f"WARNING: Sensor {meter_id} in {state['zone_id']} Zone explicitly reports device power OFF.",
                recommended_action="Inspect local power switch, circuit breaker, and auxiliary battery connection."
            )
            if alert:
                alerts_triggered.append(alert)

        # 5. Gateway Communication Disconnected
        if state['connectivity_status'] == 'DISCONNECTED' and state['power_status'] == 'ON':
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Sensor disconnected",
                severity="Warning",
                ts=ts,
                missing_mins=state['consecutive_missing'] * EXPECTED_INTERVAL_MINUTES,
                missing_count=state['consecutive_missing'],
                message=f"WARNING: Sensor {meter_id} in {state['zone_id']} Zone lost communication with local IoT Gateway.",
                recommended_action="Check LoRaWAN/ZigBee gateway connectivity, signal interference, and antenna alignment."
            )
            if alert:
                alerts_triggered.append(alert)

        # 6. Sensor Malfunction (Sensor Stuck, Drift, Spike)
        if state['active_fault'] != 'NONE':
            severity = "Critical" if state['active_fault'] in ['SENSOR_STUCK', 'SENSOR_DRIFT'] else "Warning"
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Sensor malfunction",
                severity=severity,
                ts=ts,
                missing_mins=0.0,
                missing_count=0,
                message=f"{severity.upper()}: Sensor {meter_id} in {state['zone_id']} Zone detected physical instrumentation malfunction: {state['active_fault']}.",
                recommended_action=f"Recalibrate transducer or clean flow orifice. Replace sensing element if {state['active_fault']} persists."
            )
            if alert:
                alerts_triggered.append(alert)

        # 7. Low Battery Alert
        if state['battery_pct'] <= LOW_BATTERY_THRESHOLD and state['power_status'] == 'ON':
            alert = self._trigger_or_update_alert(
                meter_id=meter_id,
                alert_category="Low battery",
                severity="Warning",
                ts=ts,
                missing_mins=0.0,
                missing_count=0,
                message=f"WARNING: Sensor {meter_id} in {state['zone_id']} Zone battery is critical ({state['battery_pct']:.1f}% remaining).",
                recommended_action="Schedule battery replacement during next maintenance cycle."
            )
            if alert:
                alerts_triggered.append(alert)

        return alerts_triggered

    def _trigger_or_update_alert(self, meter_id: str, alert_category: str, severity: str, ts: datetime.datetime, missing_mins: float, missing_count: int, message: str, recommended_action: str) -> Optional[Dict[str, Any]]:
        dedup_key = f"{meter_id}::{alert_category}"
        state = self.sensor_states[meter_id]

        if dedup_key in self.active_alerts:
            # Update existing active incident without duplicate generation
            alert = self.active_alerts[dedup_key]
            alert['last_detected_timestamp'] = ts.isoformat()
            alert['missing_duration_minutes'] = missing_mins
            alert['consecutive_missing_count'] = missing_count
            alert['message'] = message
            return None # Do not flood with duplicate alerts for ongoing incident
        else:
            # Create new incident alert
            alert = self._create_alert(
                meter_id=meter_id,
                alert_category=alert_category,
                severity=severity,
                first_detected=ts,
                ts=ts,
                message=message,
                recommended_action=recommended_action,
                missing_mins=missing_mins,
                missing_count=missing_count,
                status="OPEN"
            )
            self.active_alerts[dedup_key] = alert
            return alert

    def _create_alert(self, meter_id: str, alert_category: str, severity: str, first_detected: datetime.datetime, ts: datetime.datetime, message: str, recommended_action: str, missing_mins: float = 0.0, missing_count: int = 0, status: str = "OPEN") -> Dict[str, Any]:
        state = self.sensor_states[meter_id]
        last_valid_str = state['last_valid_timestamp'].isoformat() if state['last_valid_timestamp'] else None
        
        alert = {
            'alert_id': f"ALT_{uuid.uuid4().hex[:8].upper()}",
            'sensor_id': state['sensor_id'],
            'meter_id': meter_id,
            'campus_id': state['campus_id'],
            'zone_id': state['zone_id'],
            'sensor_type': state['sensor_type'],
            'alert_category': alert_category,
            'severity': severity,
            'first_detected_timestamp': first_detected.isoformat(),
            'last_detected_timestamp': ts.isoformat(),
            'last_received_reading_timestamp': last_valid_str,
            'missing_duration_minutes': missing_mins,
            'consecutive_missing_count': missing_count,
            'alert_message': message,
            'recommended_action': recommended_action,
            'alert_status': status,
            'acknowledged_by': None,
            'resolved_at': ts.isoformat() if status == "RESOLVED" else None
        }
        self.alert_history.append(alert)
        return alert

    def _resolve_sensor_alerts(self, meter_id: str, ts: datetime.datetime, resolution_note: str) -> int:
        keys_to_resolve = [k for k in self.active_alerts if k.startswith(f"{meter_id}::")]
        for k in keys_to_resolve:
            alert = self.active_alerts.pop(k)
            alert['alert_status'] = "RESOLVED"
            alert['resolved_at'] = ts.isoformat()
            alert['resolution_note'] = resolution_note
        return len(keys_to_resolve)

    def acknowledge_alert(self, alert_id: str, user_id: str = "operator_admin") -> Optional[Dict[str, Any]]:
        for alert in self.alert_history:
            if alert['alert_id'] == alert_id:
                alert['alert_status'] = "ACKNOWLEDGED"
                alert['acknowledged_by'] = user_id
                return alert
        return None

    def resolve_alert(self, alert_id: str, note: str = "Manually resolved by operator") -> Optional[Dict[str, Any]]:
        for alert in self.alert_history:
            if alert['alert_id'] == alert_id:
                alert['alert_status'] = "RESOLVED"
                alert['resolved_at'] = datetime.datetime.now().isoformat()
                alert['resolution_note'] = note
                # Remove from active map if present
                for k, v in list(self.active_alerts.items()):
                    if v['alert_id'] == alert_id:
                        del self.active_alerts[k]
                return alert
        return None

    def get_summary(self) -> Dict[str, Any]:
        total_sensors = len(self.sensor_states)
        healthy = sum(1 for s in self.sensor_states.values() if s['health_status'] == 'HEALTHY')
        warning = sum(1 for s in self.sensor_states.values() if s['health_status'] == 'WARNING')
        offline = sum(1 for s in self.sensor_states.values() if s['health_status'] == 'OFFLINE')
        faulty = sum(1 for s in self.sensor_states.values() if s['health_status'] == 'FAULTY')
        maintenance = sum(1 for s in self.sensor_states.values() if s['health_status'] == 'MAINTENANCE')

        open_alerts = sum(1 for a in self.alert_history if a['alert_status'] == 'OPEN')
        ack_alerts = sum(1 for a in self.alert_history if a['alert_status'] == 'ACKNOWLEDGED')
        resolved_alerts = sum(1 for a in self.alert_history if a['alert_status'] == 'RESOLVED')
        critical_alerts = sum(1 for a in self.alert_history if a['severity'] == 'Critical' and a['alert_status'] in ['OPEN', 'ACKNOWLEDGED'])
        warning_alerts = sum(1 for a in self.alert_history if a['severity'] == 'Warning' and a['alert_status'] in ['OPEN', 'ACKNOWLEDGED'])

        return {
            'total_sensors': total_sensors,
            'healthy_sensors': healthy,
            'warning_sensors': warning,
            'offline_sensors': offline,
            'faulty_sensors': faulty,
            'maintenance_sensors': maintenance,
            'open_alerts_count': open_alerts,
            'acknowledged_alerts_count': ack_alerts,
            'resolved_alerts_count': resolved_alerts,
            'critical_unresolved_count': critical_alerts,
            'warning_unresolved_count': warning_alerts
        }
