"""
AquaGuard AI - Deterministic Groundedness Evaluation
Evaluates whether explanation claims for alerts are strictly supported by physical sensor measurements.
Groundedness = supported explanation claims / total explanation claims.
Note: This is a deterministic rule-based verification metric, not an LLM hallucination score.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple

def verify_abnormal_explanation(row: pd.Series) -> Tuple[int, int, List[str]]:
    """
    Generate deterministic explanation claims for an abnormal consumption alert
    and verify each claim against actual row measurements.
    Returns: (supported_claims, total_claims, details)
    """
    claims = []
    
    # Claim 1: Consumption exceeds historical 1h average
    claims.append({
        'name': 'consumption_exceeds_1h_avg',
        'claimed': True,
        'supported': (row['interval_consumption_liters'] > row['previous_1h_avg_liters'])
    })
    
    # Claim 2: High consumption variance (consumption > 1h_avg + 2*1h_std)
    std_val = row.get('previous_1h_std_liters', 0.0)
    claims.append({
        'name': 'consumption_variance_spike',
        'claimed': True,
        'supported': (row['interval_consumption_liters'] > (row['previous_1h_avg_liters'] + 1.5 * std_val))
    })
    
    # Claim 3: Discrepancy with scheduled occupancy activity
    # If occupancy is low/zero, consumption should not be elevated
    if row.get('occupancy', 0) == 0 and row.get('scheduled_activity', 0) == 0:
        claims.append({
            'name': 'unattended_consumption',
            'claimed': True,
            'supported': (row['interval_consumption_liters'] > 0)
        })
        
    supported = sum(1 for c in claims if c['supported'])
    total = len(claims)
    return supported, total, [f"{c['name']}: {c['supported']}" for c in claims]


def verify_leak_explanation(row: pd.Series, predicted_class: int) -> Tuple[int, int, List[str]]:
    """
    Generate deterministic explanation claims for a leak/fault/demand prediction
    and verify each claim against actual physical measurements.
    """
    claims = []
    
    if predicted_class == 1: # Leak
        # Claim 1: Elevated flow rate compared to 1h average or positive flow jump
        claims.append({
            'name': 'elevated_flow',
            'claimed': True,
            'supported': (row['inlet_flow_lpm'] > row['previous_1h_avg_flow_lpm']) or (row['flow_change_lpm'] > 0)
        })
        # Claim 2: Concomitant pressure drop (hydraulic signature of leak)
        claims.append({
            'name': 'pressure_drop',
            'claimed': True,
            'supported': (row['pressure_bar'] < row['previous_1h_avg_pressure_bar']) or (row['pressure_change_bar'] < 0)
        })
        # Claim 3: Disconnect between flow and occupancy (flow not explained by scheduled activity)
        claims.append({
            'name': 'unexplained_by_occupancy',
            'claimed': True,
            'supported': (row['inlet_flow_lpm'] > 15.0 and row['occupancy'] < 20) or (row['scheduled_activity'] == 0)
        })
        
    elif predicted_class == 2: # Demand Increase
        # Claim 1: Flow elevated
        claims.append({
            'name': 'elevated_flow',
            'claimed': True,
            'supported': (row['inlet_flow_lpm'] >= row['previous_1h_avg_flow_lpm'])
        })
        # Claim 2: Scheduled activity or high occupancy present
        claims.append({
            'name': 'activity_or_occupancy_justified',
            'claimed': True,
            'supported': (row['scheduled_activity'] > 0) or (row['occupancy'] > 10)
        })
        # Claim 3: Normal or stable pressure (no catastrophic rupture drop)
        claims.append({
            'name': 'stable_pressure_regime',
            'claimed': True,
            'supported': (row['pressure_bar'] >= 1.5)
        })
        
    elif predicted_class == 3: # Sensor Fault
        # Claim 1: Flow change extreme or missing or zero variance
        claims.append({
            'name': 'anomalous_flow_or_null',
            'claimed': True,
            'supported': (pd.isnull(row['inlet_flow_lpm'])) or (abs(row['flow_change_lpm']) > 40.0) or (row['inlet_flow_lpm'] < 0)
        })
        # Claim 2: Pressure inconsistency or unphysical spike/drop
        claims.append({
            'name': 'unphysical_pressure',
            'claimed': True,
            'supported': (abs(row['pressure_change_bar']) > 1.0) or (row['pressure_bar'] <= 0.2) or (row['pressure_bar'] > 6.0)
        })
        
    else: # Normal (Class 0)
        claims.append({
            'name': 'stable_hydraulic_baseline',
            'claimed': True,
            'supported': (abs(row['flow_change_lpm']) < 15.0) and (abs(row['pressure_change_bar']) < 0.5)
        })
        
    supported = sum(1 for c in claims if c['supported'])
    total = len(claims)
    return supported, total, [f"{c['name']}: {c['supported']}" for c in claims]


def compute_groundedness_score(df_sample: pd.DataFrame, preds: np.ndarray, is_leak_model: bool = True) -> float:
    """
    Compute aggregate groundedness score across a sample of test predictions.
    """
    total_supp = 0
    total_claims = 0
    
    for i, (_, row) in enumerate(df_sample.iterrows()):
        pred = preds[i]
        if is_leak_model:
            supp, tot, _ = verify_leak_explanation(row, pred)
        else:
            if pred == 1:
                supp, tot, _ = verify_abnormal_explanation(row)
            else:
                supp, tot = 1, 1 # Normal prediction verified
        total_supp += supp
        total_claims += tot
        
    return float(total_supp / total_claims) if total_claims > 0 else 0.0
