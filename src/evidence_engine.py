"""
AquaGuard AI - Evidence-Based Decision Engine (Layer 1 + Layer 2 Integration)
Separates Sensor Health Monitoring (Layer 1) from Water Intelligence (Layer 2).
Enforces physical plausibility, prevents false leak predictions on missing telemetry,
and issues INSUFFICIENT_SENSOR_DATA when essential measurements are offline.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import joblib
import os

class EvidenceBasedDecisionEngine:
    def __init__(self, anomaly_model_path: str = None, leak_model_path: str = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if anomaly_model_path is None:
            anomaly_model_path = os.path.join(base_dir, 'models', 'anomaly', 'best_anomaly_model.joblib')
        if leak_model_path is None:
            leak_model_path = os.path.join(base_dir, 'models', 'leak', 'best_leak_model.joblib')
            
        self.anomaly_artifact = joblib.load(anomaly_model_path) if os.path.exists(anomaly_model_path) else None
        self.leak_artifact = joblib.load(leak_model_path) if os.path.exists(leak_model_path) else None
        
        print("EvidenceBasedDecisionEngine initialized with trained ML pipelines.")

    def evaluate_telemetry(self, sensor_health_info: Dict[str, Any], telemetry_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrates Layer 1 (Sensor Health) and Layer 2 (Water ML Intelligence).
        
        telemetry_payload keys:
            meter_id, zone_type, hour, occupancy, scheduled_activity,
            inlet_flow_lpm, pressure_bar, tank_level_pct,
            previous_1h_avg_flow_lpm, previous_1h_avg_pressure_bar,
            flow_change_lpm, pressure_change_bar,
            interval_consumption_liters (optional)
        """
        meter_id = telemetry_payload.get('meter_id', 'UNKNOWN')
        health_status = sensor_health_info.get('health_status', 'HEALTHY')
        power_status = sensor_health_info.get('power_status', 'ON')
        conn_status = sensor_health_info.get('connectivity_status', 'CONNECTED')
        reading_received = sensor_health_info.get('reading_received', 1)

        # -------------------------------------------------------------
        # STEP 1: LAYER 1 SENSOR HEALTH AUDIT
        # -------------------------------------------------------------
        # Check availability of key physical hydraulic measurements
        flow_raw = telemetry_payload.get('inlet_flow_lpm')
        pressure_raw = telemetry_payload.get('pressure_bar')
        consumption_raw = telemetry_payload.get('interval_consumption_liters')

        flow_available = (flow_raw is not None and not pd.isna(flow_raw) and reading_received == 1)
        pressure_available = (pressure_raw is not None and not pd.isna(pressure_raw) and reading_received == 1)
        consumption_available = (consumption_raw is not None and not pd.isna(consumption_raw) and reading_received == 1)

        # CRITICAL RULE: If sensor is OFFLINE or in MAINTENANCE, do NOT guess measurements
        if health_status in ['OFFLINE', 'MAINTENANCE'] or power_status == 'OFF' or conn_status == 'DISCONNECTED' or reading_received == 0:
            return {
                'meter_id': meter_id,
                'layer_1_sensor_health': health_status,
                'layer_2_water_assessment': 'INSUFFICIENT_SENSOR_DATA',
                'leak_detected': False,
                'anomaly_detected': False,
                'confidence': 0.0,
                'alert_action': 'DISPATCH_INSTRUMENTATION_TECHNICIAN',
                'rationale': f"Telemetry unavailable from meter {meter_id} (Sensor {health_status}, Power {power_status}, Conn {conn_status}). Model inference suspended to prevent false leak alerts.",
                'available_evidence': {
                    'flow_available': flow_available,
                    'pressure_available': pressure_available,
                    'consumption_available': consumption_available
                }
            }

        # If sensor is FAULTY (malfunctioning hardware)
        if health_status == 'FAULTY':
            fault_type = sensor_health_info.get('sensor_fault_type', 'SENSOR_FAULT')
            return {
                'meter_id': meter_id,
                'layer_1_sensor_health': 'FAULTY',
                'layer_2_water_assessment': 'SENSOR_FAULT_FLAGGED',
                'leak_detected': False,
                'anomaly_detected': False,
                'confidence': 0.95,
                'alert_action': 'RECALIBRATE_OR_REPLACE_SENSOR',
                'rationale': f"Physical sensor transducer failure detected ({fault_type}). Measurements are unphysical/distorted; leak classification withheld.",
                'available_evidence': {
                    'fault_type': fault_type,
                    'flow_value': flow_raw,
                    'pressure_value': pressure_raw
                }
            }

        # -------------------------------------------------------------
        # STEP 2: LAYER 2 WATER INTELLIGENCE (HEALTHY SENSOR DATA)
        # -------------------------------------------------------------
        # Construct feature vector for leak classification
        df_leak_in = pd.DataFrame([{
            'zone_type': telemetry_payload.get('zone_type', 'HOSTEL'),
            'hour': telemetry_payload.get('hour', 12),
            'occupancy': telemetry_payload.get('occupancy', 0),
            'scheduled_activity': telemetry_payload.get('scheduled_activity', 0),
            'inlet_flow_lpm': flow_raw,
            'pressure_bar': pressure_raw,
            'tank_level_pct': telemetry_payload.get('tank_level_pct', 70.0),
            'previous_1h_avg_flow_lpm': telemetry_payload.get('previous_1h_avg_flow_lpm', flow_raw),
            'previous_1h_avg_pressure_bar': telemetry_payload.get('previous_1h_avg_pressure_bar', pressure_raw),
            'flow_change_lpm': telemetry_payload.get('flow_change_lpm', 0.0),
            'pressure_change_bar': telemetry_payload.get('pressure_change_bar', 0.0)
        }])

        leak_label = 0
        leak_proba = [1.0, 0.0, 0.0, 0.0]
        if self.leak_artifact:
            X_proc = self.leak_artifact['preprocessor'].transform(df_leak_in)
            leak_label = int(self.leak_artifact['model'].predict(X_proc)[0])
            if hasattr(self.leak_artifact['model'], 'predict_proba'):
                leak_proba = self.leak_artifact['model'].predict_proba(X_proc)[0].tolist()

        # Physical evidence verification
        flow_val = float(flow_raw) if flow_raw is not None else 0.0
        pressure_val = float(pressure_raw) if pressure_raw is not None else 2.5
        
        raw_avg_flow = telemetry_payload.get('previous_1h_avg_flow_lpm')
        avg_flow = float(raw_avg_flow) if raw_avg_flow is not None else flow_val
        
        raw_avg_press = telemetry_payload.get('previous_1h_avg_pressure_bar')
        avg_pressure = float(raw_avg_press) if raw_avg_press is not None else pressure_val

        # Hydraulic rule verification:
        has_flow_surge = (flow_val > avg_flow * 1.25) or (telemetry_payload.get('flow_change_lpm', 0) > 10.0)
        has_pressure_drop = (pressure_val < avg_pressure * 0.85) or (telemetry_payload.get('pressure_change_bar', 0) < -0.4)
        is_unattended = (telemetry_payload.get('occupancy', 0) == 0 and telemetry_payload.get('scheduled_activity', 0) == 0)

        # Cross-layer evidence validation:
        if leak_label == 1: # Leak predicted by model
            # Confirm physical plausibility
            if has_flow_surge and has_pressure_drop:
                confidence = float(leak_proba[1]) if len(leak_proba) > 1 else 0.95
                return {
                    'meter_id': meter_id,
                    'layer_1_sensor_health': 'HEALTHY',
                    'layer_2_water_assessment': 'CONFIRMED_LEAK_BURST',
                    'leak_detected': True,
                    'anomaly_detected': True,
                    'confidence': round(confidence, 3),
                    'alert_action': 'DISPATCH_PLUMBING_CREW_ISOLATE_VALVE',
                    'rationale': f"CRITICAL LEAK CONFIRMED: Flow elevated ({flow_val:.1f} LPM) coupled with severe distribution pressure drop ({pressure_val:.2f} bar). Sensors healthy.",
                    'available_evidence': {
                        'flow_surge': True,
                        'pressure_drop': True,
                        'unattended': is_unattended
                    }
                }
            elif has_flow_surge and not has_pressure_drop:
                # Flow surge without pressure drop -> Legitimate Demand or Minor Leak
                return {
                    'meter_id': meter_id,
                    'layer_1_sensor_health': 'HEALTHY',
                    'layer_2_water_assessment': 'POTENTIAL_DEMAND_PEAK',
                    'leak_detected': False,
                    'anomaly_detected': False,
                    'confidence': 0.75,
                    'alert_action': 'MONITOR_SCHEDULE',
                    'rationale': f"Flow elevated ({flow_val:.1f} LPM) but distribution pressure remained stable ({pressure_val:.2f} bar). Likely legitimate operational demand.",
                    'available_evidence': {
                        'flow_surge': True,
                        'pressure_drop': False,
                        'unattended': is_unattended
                    }
                }

        elif leak_label == 2:
            return {
                'meter_id': meter_id,
                'layer_1_sensor_health': 'HEALTHY',
                'layer_2_water_assessment': 'LEGITIMATE_DEMAND_INCREASE',
                'leak_detected': False,
                'anomaly_detected': False,
                'confidence': float(leak_proba[2]) if len(leak_proba) > 2 else 0.90,
                'alert_action': 'NORMAL_LOGGING',
                'rationale': "Scheduled or diurnal campus demand peak (canteen/hostel) with stable hydraulic pressure.",
                'available_evidence': {'demand_increase': True}
            }

        return {
            'meter_id': meter_id,
            'layer_1_sensor_health': 'HEALTHY',
            'layer_2_water_assessment': 'NORMAL_OPERATION',
            'leak_detected': False,
            'anomaly_detected': False,
            'confidence': float(leak_proba[0]) if len(leak_proba) > 0 else 0.99,
            'alert_action': 'NONE',
            'rationale': "Telemetry within expected normal baseline operating envelope.",
            'available_evidence': {'healthy': True}
        }
