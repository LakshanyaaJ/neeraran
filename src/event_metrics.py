"""
AquaGuard AI - Event-Level Detection and Operational Tracking
Evaluates event-level detection rate, detection delay, and task success.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List

def evaluate_abnormal_event_detection(df_test: pd.DataFrame, y_pred: np.ndarray, detection_window_steps: int = 12) -> Dict[str, Any]:
    """
    Evaluate abnormal consumption event detection on test partition.
    - An abnormal event is 'detected' if at least one abnormal prediction occurs within the event window.
    - Detection delay is the time (in minutes) from event start until the first detection.
    - detection_window_steps: allowable window in 5-min steps (12 steps = 60 mins).
    """
    df_eval = df_test.copy()
    df_eval['pred_anomaly'] = y_pred
    
    # Filter to actual abnormal events
    abnormal_events = df_eval[(df_eval['is_anomaly'] == 1) & (df_eval['event_id'].notnull())]['event_id'].unique()
    total_events = len(abnormal_events)
    
    if total_events == 0:
        return {
            'total_abnormal_events': 0,
            'detected_abnormal_events': 0,
            'missed_abnormal_events': 0,
            'event_detection_rate': 0.0,
            'avg_detection_delay_mins': 0.0,
            'median_detection_delay_mins': 0.0,
            'task_success_rate': 0.0
        }
        
    detected_count = 0
    delays = []
    
    for eid in abnormal_events:
        evt_df = df_eval[df_eval['event_id'] == eid].sort_values('timestamp')
        first_ts = evt_df['timestamp'].iloc[0]
        
        # Check predictions within event
        detections = evt_df[evt_df['pred_anomaly'] == 1]
        if len(detections) > 0:
            first_det_ts = detections['timestamp'].iloc[0]
            delay_mins = (first_det_ts - first_ts).total_seconds() / 60.0
            
            # Check if within allowable detection window
            if delay_mins <= (detection_window_steps * 5.0):
                detected_count += 1
                delays.append(delay_mins)
            else:
                # Detected but too late
                pass
                
    detection_rate = detected_count / total_events if total_events > 0 else 0.0
    avg_delay = float(np.mean(delays)) if len(delays) > 0 else 0.0
    med_delay = float(np.median(delays)) if len(delays) > 0 else 0.0
    
    return {
        'total_abnormal_events': int(total_events),
        'detected_abnormal_events': int(detected_count),
        'missed_abnormal_events': int(total_events - detected_count),
        'event_detection_rate': float(detection_rate),
        'avg_detection_delay_mins': float(avg_delay),
        'median_detection_delay_mins': float(med_delay),
        'task_success_rate': float(detection_rate) # successful event detections / eligible events
    }


def evaluate_leak_event_detection(df_test: pd.DataFrame, y_pred: np.ndarray, detection_window_steps: int = 12) -> Dict[str, Any]:
    """
    Evaluate leak classification task-success on test partition:
    - Successfully detect an eligible leak event (event_label=1) within detection window.
    - Avoid classifying legitimate demand increases (event_label=2) as leaks.
    """
    df_eval = df_test.copy()
    df_eval['pred_label'] = y_pred
    
    # 1. Leak events
    leak_events = df_eval[(df_eval['event_label'] == 1) & (df_eval['event_id'].notnull())]['event_id'].unique()
    total_leaks = len(leak_events)
    
    detected_leaks = 0
    leak_delays = []
    
    for eid in leak_events:
        evt_df = df_eval[df_eval['event_id'] == eid].sort_values('timestamp')
        first_ts = evt_df['timestamp'].iloc[0]
        detections = evt_df[evt_df['pred_label'] == 1]
        if len(detections) > 0:
            first_det_ts = detections['timestamp'].iloc[0]
            delay_mins = (first_det_ts - first_ts).total_seconds() / 60.0
            if delay_mins <= (detection_window_steps * 5.0):
                detected_leaks += 1
                leak_delays.append(delay_mins)
                
    leak_detection_rate = detected_leaks / total_leaks if total_leaks > 0 else 0.0
    avg_delay = float(np.mean(leak_delays)) if len(leak_delays) > 0 else 0.0
    
    # 2. Demand events preserved without false leak alert
    demand_events = df_eval[(df_eval['event_label'] == 2) & (df_eval['event_id'].notnull())]['event_id'].unique()
    total_demand = len(demand_events)
    uncontaminated_demand = 0
    
    for eid in demand_events:
        evt_df = df_eval[df_eval['event_id'] == eid]
        # Successful if never predicted as leak (1)
        if (evt_df['pred_label'] == 1).sum() == 0:
            uncontaminated_demand += 1
            
    # Combined task-success rate:
    # All eligible target tasks (leaks to detect + demand to safely pass through)
    eligible_tasks = total_leaks + total_demand
    successful_tasks = detected_leaks + uncontaminated_demand
    task_success_rate = successful_tasks / eligible_tasks if eligible_tasks > 0 else 0.0
    
    return {
        'total_leak_events': int(total_leaks),
        'detected_leak_events': int(detected_leaks),
        'missed_leak_events': int(total_leaks - detected_leaks),
        'leak_detection_rate': float(leak_detection_rate),
        'avg_leak_detection_delay_mins': float(avg_delay),
        'total_demand_events': int(total_demand),
        'safely_passed_demand_events': int(uncontaminated_demand),
        'task_success_rate': float(task_success_rate)
    }
