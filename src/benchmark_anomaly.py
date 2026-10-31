import pandas as pd
import numpy as np
import time
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

print("Testing Anomaly Model Training Speed...")
df_abn = pd.read_csv("data/synthetic/abnormal_consumption.csv")
num_cols = ['hour', 'day_of_week', 'is_weekend', 'is_holiday', 'occupancy', 
            'scheduled_activity', 'temperature_c', 'interval_consumption_liters', 
            'previous_1h_avg_liters', 'previous_24h_avg_liters', 'previous_1h_std_liters']

# Filter normal training data
normal_train = df_abn[(df_abn['is_anomaly'] == 0) & (pd.to_datetime(df_abn['timestamp']) <= '2026-09-01 23:56:30')][num_cols]
print(f"Normal train rows: {len(normal_train)}")

# Impute
imputer = SimpleImputer(strategy='median')
X_norm = imputer.fit_transform(normal_train)
scaler = StandardScaler()
X_norm_scaled = scaler.fit_transform(X_norm)

# 1. Isolation Forest
t0 = time.time()
iso = IsolationForest(n_estimators=100, contamination=0.005, random_state=42, n_jobs=-1)
iso.fit(X_norm)
t1 = time.time()
print(f"Isolation Forest fit on {len(X_norm)} rows: {t1 - t0:.2f}s")

# 2. LOF (novelty=True) on 20,000 subsample
t0 = time.time()
np.random.seed(42)
sub_idx = np.random.choice(len(X_norm_scaled), size=20000, replace=False)
lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.005, n_jobs=-1)
lof.fit(X_norm_scaled[sub_idx])
t1 = time.time()
print(f"LOF fit on 20,000 rows: {t1 - t0:.2f}s")

# 3. One-Class SVM on 20,000 subsample
t0 = time.time()
ocsvm = OneClassSVM(kernel='rbf', gamma='scale', nu=0.005)
ocsvm.fit(X_norm_scaled[sub_idx])
t1 = time.time()
print(f"One-Class SVM fit on 20,000 rows: {t1 - t0:.2f}s")
