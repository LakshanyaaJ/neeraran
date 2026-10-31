"""
AquaGuard AI - Evaluation Metrics and Benchmarking Suite
Calculates row-level, event-level, latency, and operational metrics.
"""

import numpy as np
import pandas as pd
import time
import os
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, precision_recall_curve, auc,
    classification_report
)

def evaluate_binary_anomaly(y_true, y_pred, y_scores=None):
    """
    Evaluate binary unsupervised anomaly detection performance.
    y_true: 0 = normal, 1 = abnormal
    y_pred: 0 = normal, 1 = abnormal
    y_scores: anomaly score (higher = more anomalous)
    """
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    roc_auc = np.nan
    pr_auc = np.nan
    if y_scores is not None:
        try:
            roc_auc = roc_auc_score(y_true, y_scores)
            p_curve, r_curve, _ = precision_recall_curve(y_true, y_scores)
            pr_auc = auc(r_curve, p_curve)
        except Exception:
            pass
            
    return {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'specificity': float(specificity),
        'fpr': float(fpr),
        'fnr': float(fnr),
        'tp': int(tp),
        'fp': int(fp),
        'tn': int(tn),
        'fn': int(fn),
        'roc_auc': float(roc_auc) if not np.isnan(roc_auc) else None,
        'pr_auc': float(pr_auc) if not np.isnan(pr_auc) else None
    }


def evaluate_multiclass_leak(y_true, y_pred, y_proba=None):
    """
    Evaluate multiclass leak identification performance.
    Classes:
    0 = normal / non-leak baseline
    1 = leak
    2 = demand_increase
    3 = sensor_fault
    """
    labels = [0, 1, 2, 3]
    class_names = ['normal', 'leak', 'demand_increase', 'sensor_fault']
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    acc = accuracy_score(y_true, y_pred)
    macro_p = precision_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    macro_r = recall_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average='macro', zero_division=0)
    weighted_f1 = f1_score(y_true, y_pred, labels=labels, average='weighted', zero_division=0)
    
    per_class_p = precision_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    per_class_r = recall_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    per_class_f1 = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    
    # Specific leak metrics (class 1)
    # tp: leak predicted as leak
    tp_leak = cm[1, 1]
    fn_leak = cm[1, :].sum() - tp_leak
    fp_leak = cm[:, 1].sum() - tp_leak
    tn_leak = cm.sum() - (tp_leak + fn_leak + fp_leak)
    
    leak_precision = tp_leak / (tp_leak + fp_leak) if (tp_leak + fp_leak) > 0 else 0.0
    leak_recall = tp_leak / (tp_leak + fn_leak) if (tp_leak + fn_leak) > 0 else 0.0
    leak_fpr = fp_leak / (fp_leak + tn_leak) if (fp_leak + tn_leak) > 0 else 0.0
    leak_fnr = fn_leak / (fn_leak + tp_leak) if (fn_leak + tp_leak) > 0 else 0.0
    
    # Specific critical misclassification rates:
    # Demand increase (class 2) misclassified as Leak (class 1)
    demand_total = cm[2, :].sum()
    demand_to_leak = cm[2, 1]
    demand_to_leak_rate = demand_to_leak / demand_total if demand_total > 0 else 0.0
    
    # Sensor fault (class 3) misclassified as Leak (class 1)
    sensor_total = cm[3, :].sum()
    sensor_to_leak = cm[3, 1]
    sensor_to_leak_rate = sensor_to_leak / sensor_total if sensor_total > 0 else 0.0
    
    # Multiclass ROC-AUC (ovr)
    roc_auc_ovr = np.nan
    if y_proba is not None:
        try:
            roc_auc_ovr = roc_auc_score(y_true, y_proba, multi_class='ovr', average='macro')
        except Exception:
            pass
            
    res = {
        'accuracy': float(acc),
        'macro_precision': float(macro_p),
        'macro_recall': float(macro_r),
        'macro_f1': float(macro_f1),
        'weighted_f1': float(weighted_f1),
        'leak_precision': float(leak_precision),
        'leak_recall': float(leak_recall),
        'leak_fpr': float(leak_fpr),
        'leak_fnr': float(leak_fnr),
        'demand_to_leak_misclassification_rate': float(demand_to_leak_rate),
        'sensor_to_leak_misclassification_rate': float(sensor_to_leak_rate),
        'confusion_matrix': cm.tolist(),
        'multiclass_roc_auc': float(roc_auc_ovr) if not np.isnan(roc_auc_ovr) else None
    }
    
    for i, name in enumerate(class_names):
        res[f'{name}_precision'] = float(per_class_p[i])
        res[f'{name}_recall'] = float(per_class_r[i])
        res[f'{name}_f1'] = float(per_class_f1[i])
        
    return res


def benchmark_inference_latency(pipeline, X_sample, n_warmup=10, n_runs=100):
    """
    Measure single-record and batch inference latency.
    Reports average, median, and P95 latency in milliseconds.
    """
    # Warmup
    for _ in range(n_warmup):
        _ = pipeline.predict(X_sample.iloc[:1])
        
    single_latencies = []
    # Test on individual single-row queries
    test_indices = np.random.choice(len(X_sample), size=min(n_runs, len(X_sample)), replace=False)
    for idx in test_indices:
        row = X_sample.iloc[[idx]]
        t0 = time.perf_counter()
        _ = pipeline.predict(row)
        t1 = time.perf_counter()
        single_latencies.append((t1 - t0) * 1000.0) # ms
        
    # Batch latency (1000 items)
    batch_size = min(1000, len(X_sample))
    X_batch = X_sample.iloc[:batch_size]
    t0_b = time.perf_counter()
    _ = pipeline.predict(X_batch)
    t1_b = time.perf_counter()
    batch_total_ms = (t1_b - t0_b) * 1000.0
    batch_per_sample_ms = batch_total_ms / batch_size
    
    return {
        'avg_latency_ms': float(np.mean(single_latencies)),
        'median_latency_ms': float(np.median(single_latencies)),
        'p95_latency_ms': float(np.percentile(single_latencies, 95)),
        'batch_1000_total_ms': float(batch_total_ms),
        'batch_per_sample_ms': float(batch_per_sample_ms)
    }


def get_model_size_kb(filepath: str) -> float:
    """Return model file size in kilobytes."""
    if os.path.exists(filepath):
        return round(os.path.getsize(filepath) / 1024.0, 2)
    return 0.0
