"""
AquaGuard AI - Hydraulic Recovery and Intervention Simulation
Simulates the operational recovery lifecycle:
1. Leak begins (t_start)
2. Model detects leak (t_detect) -> Time to detection
3. Alert generated (t_alert = t_detect + delta_alert)
4. Recommendation issued (t_rec = t_alert + delta_rec)
5. Simulated operator approval occurs (t_approval = t_rec + delta_approval)
6. Simulated repair takes place (duration = delta_repair)
7. Return to stable normal range (t_stable = t_approval + delta_repair + delta_stabilize)
Total Recovery Time = t_stable - t_start.

Note: Clearly labeled as a standardized operational simulation with identical intervention assumptions across all models.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Standardized operational intervention policy assumptions (in minutes)
SIM_ALERT_GENERATION_MINS = 2.0    # Automated dispatch queue latency
SIM_RECOMMENDATION_MINS = 3.0      # Automated diagnostic report & isolation valve advice
SIM_OPERATOR_APPROVAL_MINS = 15.0  # Facility technician acknowledgment
SIM_REPAIR_DURATION_MINS = 60.0    # Physical valve shutoff or pipe repair
SIM_STABILIZATION_MINS = 10.0      # Hydraulic stabilization post-repair

def simulate_event_recovery(df_event: pd.DataFrame, preds: np.ndarray, leak_class: int = 1) -> Dict[str, Any]:
    """
    Simulate recovery lifecycle for a single leak event.
    df_event must be sorted by timestamp.
    """
    start_time = df_event['timestamp'].iloc[0]
    total_duration_mins = (df_event['timestamp'].iloc[-1] - start_time).total_seconds() / 60.0 + 5.0
    
    detection_indices = np.where(preds == leak_class)[0]
    if len(detection_indices) == 0:
        # Undetected leak: runs unmitigated for full duration without intervention
        return {
            'detected': False,
            'time_to_detection_mins': total_duration_mins,
            'time_to_recommendation_mins': np.nan,
            'approval_delay_mins': np.nan,
            'repair_duration_mins': np.nan,
            'stabilization_mins': np.nan,
            'total_recovery_time_mins': total_duration_mins,
            'water_saved_ratio': 0.0
        }
        
    first_det_idx = detection_indices[0]
    detect_time = df_event['timestamp'].iloc[first_det_idx]
    ttd = (detect_time - start_time).total_seconds() / 60.0
    
    ttr = ttd + SIM_ALERT_GENERATION_MINS + SIM_RECOMMENDATION_MINS
    total_intervention = (
        SIM_ALERT_GENERATION_MINS +
        SIM_RECOMMENDATION_MINS +
        SIM_OPERATOR_APPROVAL_MINS +
        SIM_REPAIR_DURATION_MINS +
        SIM_STABILIZATION_MINS
    )
    total_recovery = ttd + total_intervention
    
    # Water saved ratio: fraction of leak duration truncated post-repair
    saved_mins = max(0.0, total_duration_mins - total_recovery)
    saved_ratio = saved_mins / total_duration_mins if total_duration_mins > 0 else 0.0
    
    return {
        'detected': True,
        'time_to_detection_mins': float(ttd),
        'time_to_recommendation_mins': float(ttr),
        'approval_delay_mins': float(SIM_OPERATOR_APPROVAL_MINS),
        'repair_duration_mins': float(SIM_REPAIR_DURATION_MINS),
        'stabilization_mins': float(SIM_STABILIZATION_MINS),
        'total_recovery_time_mins': float(total_recovery),
        'water_saved_ratio': float(saved_ratio)
    }


def simulate_cohort_recovery(df_test: pd.DataFrame, y_pred: np.ndarray, is_leak_model: bool = True) -> Dict[str, Any]:
    """
    Run simulated recovery for all target test events.
    """
    df_eval = df_test.copy()
    df_eval['pred'] = y_pred
    
    target_label = 1 if is_leak_model else 1
    label_col = 'event_label' if is_leak_model else 'is_anomaly'
    
    events = df_eval[(df_eval[label_col] == target_label) & (df_eval['event_id'].notnull())]['event_id'].unique()
    
    if len(events) == 0:
        return {
            'n_events': 0,
            'avg_time_to_detection_mins': 0.0,
            'avg_time_to_recommendation_mins': 0.0,
            'simulated_approval_delay_mins': SIM_OPERATOR_APPROVAL_MINS,
            'simulated_repair_duration_mins': SIM_REPAIR_DURATION_MINS,
            'avg_total_recovery_time_mins': 0.0,
            'avg_water_saved_ratio': 0.0
        }
        
    sim_results = []
    for eid in events:
        sub = df_eval[df_eval['event_id'] == eid].sort_values('timestamp')
        sub_preds = sub['pred'].values
        res = simulate_event_recovery(sub, sub_preds, leak_class=target_label)
        sim_results.append(res)
        
    avg_ttd = np.mean([r['time_to_detection_mins'] for r in sim_results])
    avg_ttr = np.mean([r['time_to_recommendation_mins'] for r in sim_results if r['detected']]) if any(r['detected'] for r in sim_results) else 0.0
    avg_tot = np.mean([r['total_recovery_time_mins'] for r in sim_results])
    avg_saved = np.mean([r['water_saved_ratio'] for r in sim_results])
    
    return {
        'n_events': len(events),
        'avg_time_to_detection_mins': float(avg_ttd),
        'avg_time_to_recommendation_mins': float(avg_ttr),
        'simulated_approval_delay_mins': float(SIM_OPERATOR_APPROVAL_MINS),
        'simulated_repair_duration_mins': float(SIM_REPAIR_DURATION_MINS),
        'avg_total_recovery_time_mins': float(avg_tot),
        'avg_water_saved_ratio': float(avg_saved)
    }
