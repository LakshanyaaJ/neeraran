"""
Compute exact Train and Test evaluation metrics for all 6 trained models
and export:
1. results/model_train_test_accuracy.csv (Comprehensive train/test metrics)
2. data/splits/ (train, val, test CSV datasets)
"""

import os
import sys

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('..'))

import joblib
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from src.data_loader import load_raw_data, split_dataset_event_aware, ABNORMAL_CANDIDATE_FEATURES, LEAK_CANDIDATE_FEATURES

def run():
    print("Loading data...")
    df_abn, df_leak = load_raw_data()
    
    print("Partitioning event-aware splits...")
    split_abn = split_dataset_event_aware(df_abn, 0.70, 0.15)
    train_abn, val_abn, test_abn = split_abn['train'], split_abn['val'], split_abn['test']
    
    split_leak = split_dataset_event_aware(df_leak, 0.70, 0.15)
    train_leak, val_leak, test_leak = split_leak['train'], split_leak['val'], split_leak['test']
    
    # -------------------------------------------------------------------------
    # 1. EXPORT DATASET CSVs TO data/splits/
    # -------------------------------------------------------------------------
    splits_dir = os.path.join('data', 'splits')
    os.makedirs(splits_dir, exist_ok=True)
    
    print("Exporting split dataset CSVs...")
    train_abn.to_csv(os.path.join(splits_dir, 'train_abnormal_consumption.csv'), index=False)
    val_abn.to_csv(os.path.join(splits_dir, 'val_abnormal_consumption.csv'), index=False)
    test_abn.to_csv(os.path.join(splits_dir, 'test_abnormal_consumption.csv'), index=False)
    
    train_leak.to_csv(os.path.join(splits_dir, 'train_leak_identification.csv'), index=False)
    val_leak.to_csv(os.path.join(splits_dir, 'val_leak_identification.csv'), index=False)
    test_leak.to_csv(os.path.join(splits_dir, 'test_leak_identification.csv'), index=False)
    print("Split CSVs exported successfully to data/splits/.")

    # -------------------------------------------------------------------------
    # 2. EVALUATE TRAIN AND TEST PERFORMANCE METRICS
    # -------------------------------------------------------------------------
    results = []
    
    # Load Anomaly Models
    iso_art = joblib.load('models/anomaly/isolation_forest.joblib')
    iso_model = iso_art['model']
    iso_prep = iso_art['preprocessor']
    iso_thresh = iso_art['threshold']
    
    ocsvm_art = joblib.load('models/anomaly/one_class_svm.joblib')
    ocsvm_model = ocsvm_art['model']
    ocsvm_prep = ocsvm_art['preprocessor']
    ocsvm_thresh = ocsvm_art['threshold']
    
    lof_art = joblib.load('models/anomaly/lof.joblib')
    lof_model = lof_art['model']
    lof_prep = lof_art['preprocessor']
    lof_thresh = lof_art['threshold']
    
    # Anomaly Data
    X_train_abn_proc = iso_prep.transform(train_abn[ABNORMAL_CANDIDATE_FEATURES])
    y_train_abn = train_abn['is_anomaly'].values
    
    X_test_abn_proc = iso_prep.transform(test_abn[ABNORMAL_CANDIDATE_FEATURES])
    y_test_abn = test_abn['is_anomaly'].values
    
    # --- Isolation Forest ---
    print("Evaluating Isolation Forest...")
    s_tr_iso = -iso_model.decision_function(X_train_abn_proc)
    p_tr_iso = (s_tr_iso >= iso_thresh).astype(int)
    s_te_iso = -iso_model.decision_function(X_test_abn_proc)
    p_te_iso = (s_te_iso >= iso_thresh).astype(int)
    
    results.append({
        'Domain': 'Abnormal Consumption Detection',
        'Model': 'Isolation Forest',
        'Train_Accuracy': accuracy_score(y_train_abn, p_tr_iso),
        'Test_Accuracy': accuracy_score(y_test_abn, p_te_iso),
        'Train_F1': f1_score(y_train_abn, p_tr_iso, zero_division=0),
        'Test_F1': f1_score(y_test_abn, p_te_iso, zero_division=0),
        'Train_Precision': precision_score(y_train_abn, p_tr_iso, zero_division=0),
        'Test_Precision': precision_score(y_test_abn, p_te_iso, zero_division=0),
        'Train_Recall': recall_score(y_train_abn, p_tr_iso, zero_division=0),
        'Test_Recall': recall_score(y_test_abn, p_te_iso, zero_division=0),
        'Selected_For_Production': 'NO (Baseline)'
    })
    
    # --- One-Class SVM ---
    print("Evaluating One-Class SVM...")
    # Evaluate on a representative sample of train to maintain reasonable compute time
    sub_idx = np.random.RandomState(42).choice(len(train_abn), size=30000, replace=False)
    X_tr_sub = iso_prep.transform(train_abn.iloc[sub_idx][ABNORMAL_CANDIDATE_FEATURES])
    y_tr_sub = train_abn.iloc[sub_idx]['is_anomaly'].values
    
    s_tr_oc = -ocsvm_model.decision_function(X_tr_sub)
    p_tr_oc = (s_tr_oc >= ocsvm_thresh).astype(int)
    s_te_oc = -ocsvm_model.decision_function(X_test_abn_proc)
    p_te_oc = (s_te_oc >= ocsvm_thresh).astype(int)
    
    results.append({
        'Domain': 'Abnormal Consumption Detection',
        'Model': 'One-Class SVM',
        'Train_Accuracy': accuracy_score(y_tr_sub, p_tr_oc),
        'Test_Accuracy': accuracy_score(y_test_abn, p_te_oc),
        'Train_F1': f1_score(y_tr_sub, p_tr_oc, zero_division=0),
        'Test_F1': f1_score(y_test_abn, p_te_oc, zero_division=0),
        'Train_Precision': precision_score(y_tr_sub, p_tr_oc, zero_division=0),
        'Test_Precision': precision_score(y_test_abn, p_te_oc, zero_division=0),
        'Train_Recall': recall_score(y_tr_sub, p_tr_oc, zero_division=0),
        'Test_Recall': recall_score(y_test_abn, p_te_oc, zero_division=0),
        'Selected_For_Production': 'YES (Winner)'
    })
    
    # --- Local Outlier Factor ---
    print("Evaluating LOF...")
    s_tr_lof = -lof_model.decision_function(X_tr_sub[:10000])
    p_tr_lof = (s_tr_lof >= lof_thresh).astype(int)
    s_te_lof = -lof_model.decision_function(X_test_abn_proc)
    p_te_lof = (s_te_lof >= lof_thresh).astype(int)
    
    results.append({
        'Domain': 'Abnormal Consumption Detection',
        'Model': 'Local Outlier Factor',
        'Train_Accuracy': accuracy_score(y_tr_sub[:10000], p_tr_lof),
        'Test_Accuracy': accuracy_score(y_test_abn, p_te_lof),
        'Train_F1': f1_score(y_tr_sub[:10000], p_tr_lof, zero_division=0),
        'Test_F1': f1_score(y_test_abn, p_te_lof, zero_division=0),
        'Train_Precision': precision_score(y_tr_sub[:10000], p_tr_lof, zero_division=0),
        'Test_Precision': precision_score(y_test_abn, p_te_lof, zero_division=0),
        'Train_Recall': recall_score(y_tr_sub[:10000], p_tr_lof, zero_division=0),
        'Test_Recall': recall_score(y_test_abn, p_te_lof, zero_division=0),
        'Selected_For_Production': 'NO'
    })
    
    # --- Leak Models ---
    xgb_art = joblib.load('models/leak/xgboost_classifier.joblib')
    xgb_model = xgb_art['model']
    xgb_prep = xgb_art['preprocessor']
    
    rf_art = joblib.load('models/leak/random_forest.joblib')
    rf_model = rf_art['model']
    
    et_art = joblib.load('models/leak/extra_trees.joblib')
    et_model = et_art['model']
    
    X_train_leak_proc = xgb_prep.transform(train_leak[LEAK_CANDIDATE_FEATURES])
    y_train_leak = train_leak['event_label'].values
    
    X_test_leak_proc = xgb_prep.transform(test_leak[LEAK_CANDIDATE_FEATURES])
    y_test_leak = test_leak['event_label'].values
    
    # XGBoost
    print("Evaluating XGBoost...")
    p_tr_xgb = xgb_model.predict(X_train_leak_proc)
    p_te_xgb = xgb_model.predict(X_test_leak_proc)
    
    results.append({
        'Domain': 'Hydraulic Leak Identification',
        'Model': 'XGBoost Classifier',
        'Train_Accuracy': accuracy_score(y_train_leak, p_tr_xgb),
        'Test_Accuracy': accuracy_score(y_test_leak, p_te_xgb),
        'Train_F1': f1_score(y_train_leak, p_tr_xgb, average='weighted', zero_division=0),
        'Test_F1': f1_score(y_test_leak, p_te_xgb, average='weighted', zero_division=0),
        'Train_Precision': precision_score(y_train_leak == 1, p_tr_xgb == 1, zero_division=0),
        'Test_Precision': precision_score(y_test_leak == 1, p_te_xgb == 1, zero_division=0),
        'Train_Recall': recall_score(y_train_leak == 1, p_tr_xgb == 1, zero_division=0),
        'Test_Recall': recall_score(y_test_leak == 1, p_te_xgb == 1, zero_division=0),
        'Selected_For_Production': 'YES (Winner)'
    })
    
    # Random Forest
    print("Evaluating Random Forest...")
    p_tr_rf = rf_model.predict(X_train_leak_proc)
    p_te_rf = rf_model.predict(X_test_leak_proc)
    
    results.append({
        'Domain': 'Hydraulic Leak Identification',
        'Model': 'Random Forest Classifier',
        'Train_Accuracy': accuracy_score(y_train_leak, p_tr_rf),
        'Test_Accuracy': accuracy_score(y_test_leak, p_te_rf),
        'Train_F1': f1_score(y_train_leak, p_tr_rf, average='weighted', zero_division=0),
        'Test_F1': f1_score(y_test_leak, p_te_rf, average='weighted', zero_division=0),
        'Train_Precision': precision_score(y_train_leak == 1, p_tr_rf == 1, zero_division=0),
        'Test_Precision': precision_score(y_test_leak == 1, p_te_rf == 1, zero_division=0),
        'Train_Recall': recall_score(y_train_leak == 1, p_tr_rf == 1, zero_division=0),
        'Test_Recall': recall_score(y_test_leak == 1, p_te_rf == 1, zero_division=0),
        'Selected_For_Production': 'NO'
    })
    
    # Extra Trees
    print("Evaluating Extra Trees...")
    p_tr_et = et_model.predict(X_train_leak_proc)
    p_te_et = et_model.predict(X_test_leak_proc)
    
    results.append({
        'Domain': 'Hydraulic Leak Identification',
        'Model': 'Extra Trees Classifier',
        'Train_Accuracy': accuracy_score(y_train_leak, p_tr_et),
        'Test_Accuracy': accuracy_score(y_test_leak, p_te_et),
        'Train_F1': f1_score(y_train_leak, p_tr_et, average='weighted', zero_division=0),
        'Test_F1': f1_score(y_test_leak, p_te_et, average='weighted', zero_division=0),
        'Train_Precision': precision_score(y_train_leak == 1, p_tr_et == 1, zero_division=0),
        'Test_Precision': precision_score(y_test_leak == 1, p_te_et == 1, zero_division=0),
        'Train_Recall': recall_score(y_train_leak == 1, p_tr_et == 1, zero_division=0),
        'Test_Recall': recall_score(y_test_leak == 1, p_te_et == 1, zero_division=0),
        'Selected_For_Production': 'NO'
    })
    
    df_res = pd.DataFrame(results)
    
    out_csv = os.path.join('results', 'model_train_test_accuracy.csv')
    df_res.to_csv(out_csv, index=False)
    print(f"\nSaved Train & Test performance metrics to: {out_csv}")
    
    # Also save to docs/ml_audit/
    out_audit_csv = os.path.join('docs', 'ml_audit', 'model_train_test_accuracy.csv')
    df_res.to_csv(out_audit_csv, index=False)
    print(f"Saved duplicate copy to: {out_audit_csv}")
    
    print("\n--- RESULTS PREVIEW ---")
    print(df_res[['Model', 'Train_Accuracy', 'Test_Accuracy', 'Train_F1', 'Test_F1', 'Selected_For_Production']].to_string())

if __name__ == '__main__':
    run()
