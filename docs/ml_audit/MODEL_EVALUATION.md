# AquaGuard AI — Comprehensive Model Evaluation Audit

**Auditor:** Senior Machine Learning Auditor & Statistical Validation Specialist  
**Audit Date:** October 31, 2026  
**Audited Models:**
1. **Model 1:** Isolation Forest (Unsupervised Abnormal Consumption Detector)
2. **Model 2:** XGBoost Classifier (Multiclass Hydraulic Regime & Leak Classifier)

---

## 1. Model 1 Audit: Isolation Forest (Abnormal Water Consumption)

### 1.1 Objective and Configuration
- **Model Type:** Scikit-Learn `IsolationForest`
- **Objective:** Detect abnormal consumption anomalies without access to ground truth labels during training.
- **Training Strategy:** Fitted exclusively on *normal training observations* ($is\_anomaly = 0$), adhering to unsupervised novelty detection standards.
- **Configured Parameters:**
  - `n_estimators`: 150 (number of random isolation trees)
  - `contamination`: 0.005 (assumed proportion of outliers in the data)
  - `max_samples`: `'auto'` (draws 256 samples per tree)
  - `max_features`: 1.0 (uses all 17 preprocessed features)
  - `random_state`: 42 (deterministic reproducibility)
  - `n_jobs`: -1 (parallel CPU execution)

### 1.2 Decision Threshold Interpretation
In scikit-learn, `decision_function(X)` returns the anomaly score:
$$\text{Score}(x) = 2^{-\frac{E(h(x))}{c(n)}}$$
Scikit-learn offsets this such that scores below 0.0 correspond to anomalies under the configured contamination. In AquaGuard AI's training pipeline, the negative decision score was calibrated against validation PR-AUC, yielding an optimal decision boundary of **$\tau = 0.0108$**.

### 1.3 Untouched Test Set Evaluation (46,656 Observations)

| Metric | Calibrated Threshold ($\tau = 0.0108$) | Default Threshold ($\tau = 0.0$) | One-Class SVM Benchmark |
|---|:---:|:---:|:---:|
| **Accuracy** | **0.9955 (99.55%)** | 0.9934 (99.34%) | 0.9989 (99.89%) |
| **Precision** | **0.1529 (15.29%)** | 0.1438 (14.38%) | **0.7379 (73.79%)** |
| **Recall** | **0.2376 (23.76%)** | 0.4158 (41.58%) | **0.7525 (75.25%)** |
| **F1-Score** | **0.1860** | 0.2137 | **0.7451** |
| **Specificity** | 0.9971 (99.71%) | 0.9946 (99.46%) | 0.9994 (99.94%) |
| **False Positive Rate (FPR)** | 0.002857 (0.2857%) | 0.005391 (0.5391%) | 0.000580 (0.0580%) |
| **False Negative Rate (FNR)** | **0.7624 (76.24%)** | 0.5842 (58.42%) | **0.2475 (24.75%)** |
| **ROC-AUC** | 0.8969 | 0.8969 | 0.7857 |
| **PR-AUC** | 0.2225 | 0.2225 | 0.7162 |

#### Confusion Matrix (Calibrated Threshold):
```
                       Predicted Normal (0)    Predicted Anomaly (1)
Actual Normal (0)             46,422                   133   (False Positives)
Actual Anomaly (1)                77                    24   (True Positives)
```

### 1.4 Critical Anomaly Detection Insights
1. **The Deception of Accuracy:** Isolation Forest achieves **99.55% accuracy**, yet has an F1-score of only **0.1860**. Because anomalies constitute only 0.22% of the test partition, a naive model predicting "Normal" on every single row would achieve 99.78% accuracy. **Accuracy is an invalid metric for highly imbalanced anomaly detection.**
2. **High False Negative Rate (76.2% Missed Anomalies):** The model misses 77 out of 101 consumption anomalies in the test set. In a university campus setting, missed anomalies mean prolonged unmetered losses or water tank overflows go unnoticed.
3. **High False Discovery (84.7% False Alarm Ratio):** Out of 157 alarms raised by the model, only 24 are true anomalies (Precision = 15.29%). If campus technicians are dispatched for every alarm, 85 out of 100 trips will be wild goose chases, causing alarm fatigue.
4. **Why One-Class SVM Outperforms Isolation Forest:** Isolation Forest constructs axis-aligned orthogonal partitions. Campus water demand follows smooth diurnal sinusoidal curves with strong covariance between occupancy and hour of day. One-Class SVM with an RBF kernel maps this non-linear manifold into a reproducing kernel Hilbert space, achieving an F1 of **0.7451** (4x higher than Isolation Forest).

---

## 2. Model 2 Audit: XGBoost Classifier (Leak Identification)

### 2.1 Objective and Configuration
- **Model Type:** `xgboost.XGBClassifier`
- **Objective:** Classify 5-minute hydraulic observations into 4 operational states:
  - Class 0: Baseline / Non-Leak (Routine water usage)
  - Class 1: True Pipe Leak (Physical hydraulic rupture)
  - Class 2: Legitimate Demand Increase (Canteen/Hostel surge, cleaning)
  - Class 3: Sensor Fault (Drift, stuck transducer, telemetry dropout)
- **Configured Parameters:**
  - `n_estimators`: 150
  - `max_depth`: 5
  - `learning_rate`: 0.08
  - `subsample`: 0.8
  - `colsample_bytree`: 0.8
  - `objective`: `'multi:softprob'`
  - `num_class`: 4
  - `tree_method`: `'hist'`
  - `sample_weight`: Balanced per-sample inverse frequency weights (computed via scikit-learn)

### 2.2 Untouched Test Set Evaluation (46,656 Observations)

| Metric | Measured Value | Operational Benchmark | Assessment |
|---|:---:|:---:|:---:|
| **Overall Accuracy** | **0.9979 (99.79%)** | > 0.98 | PASS |
| **Macro F1-Score** | **0.6254** | > 0.60 | PASS WITH LIMITATIONS |
| **Weighted F1-Score** | **0.9978** | > 0.99 | PASS |
| **ROC-AUC (One-vs-Rest)** | **0.7989** | > 0.75 | PASS |
| **Multiclass Log Loss** | **0.0145** | < 0.05 | EXCELLENT |
| **Single-Sample Latency** | **1.14 ms (P95: 1.34 ms)** | < 10.0 ms | PRODUCTION READY |

### 2.3 Multiclass Performance Breakdown by Class

| Class ID & Name | Precision | Recall | F1-Score | Support (Rows) | Operational Significance |
|---|:---:|:---:|:---:|:---:|---|
| **Class 0: Normal / Baseline** | **0.9991** | **0.9989** | **0.9990** | 46,515 | Excellent baseline retention; minimal false alerts |
| **Class 1: True Pipe Leak** | **0.9737** | **1.0000** | **0.9867** | 74 | **Zero missed leaks! Perfect 100% recall** |
| **Class 2: Demand Surge** | **0.3582** | **0.9231** | **0.5161** | 26 | Captures demand surges, but some benign noise confused |
| **Class 3: Sensor Fault** | **0.0000** | **0.0000** | **0.0000** | 41 | **CRITICAL LIMITATION: Fails on sensor faults in ML** |

#### Confusion Matrix (Multiclass):
```
Actual \ Predicted       Class 0 (Normal)   Class 1 (Leak)   Class 2 (Demand)   Class 3 (Sensor)
Class 0 (Normal)              46,464               2                49                  0
Class 1 (True Leak)                0              74                 0                  0
Class 2 (Demand Surge)             2               0                24                  0
Class 3 (Sensor Fault)            41               0                 0                  0
```

### 2.4 Deep Dive into Class 1 (True Pipe Leaks)
- **Zero Missed Leaks (Recall = 100.0%):** All 74 pipe leak intervals in the test set were detected without exception.
- **Near-Zero False Leak Alarms (Precision = 97.37%):** Out of 46,582 non-leak records, exactly **2 false leak predictions** occurred (FPR = 0.0043%).
- **Cross-Class Separation:** Zero demand surges (Class 2) and zero sensor faults (Class 3) were misclassified as leaks. The model successfully distinguished benign water surges from physical pipe ruptures.

### 2.5 Critical Finding: The Failure on Class 3 (Sensor Faults)
The model achieved **0.0% Recall and 0.0% F1** on Class 3 (Sensor Faults) in the test partition, classifying all 41 sensor fault records as Class 0 (Normal).
- **Root Cause:** In the test set, sensor fault events (`sensor_stuck`, `sensor_spike`) occurred during quiescent intervals where measured flow and pressure remained static. A static sensor reading is mathematically indistinguishable from normal steady-state water demand when evaluated on hydraulic features alone.
- **Why Layer 1 Decoupling is Essential:** This finding demonstrates why machine learning on hydraulic data alone cannot solve IoT reliability. Our **Layer 1 Sensor Health Monitoring Service** bypasses the ML model entirely by tracking heartbeat packet loss, battery drop, and consecutive variance to flag `FAULTY` and `OFFLINE` hardware deterministically.

---

## 3. Probability Calibration Audit (XGBoost)

We computed the Brier score ($BS = \frac{1}{N} \sum_{i=1}^N (p_{ic} - y_{ic})^2$) for each class:
- **Class 0 (Normal):** $BS = 0.001930$
- **Class 1 (True Leak):** $BS = 0.000043$ (Extremely sharp and well-calibrated)
- **Class 2 (Demand Surge):** $BS = 0.000751$
- **Class 3 (Sensor Fault):** $BS = 0.001132$

**Calibration Verdict:** The predicted probability for Class 1 (Leak) is trustworthy and reflects genuine hydraulic divergence. For Class 2, probabilities tend to be slightly overconfident between 0.60 and 0.85, warranting human confirmation before scheduling maintenance.
