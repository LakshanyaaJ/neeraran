# NEERARAN – Water Demand Forecasting Module

High-performance, physically grounded, leak-free hourly water consumption forecasting module for university and industrial campuses. Predicts multi-horizon demand across 24h, 48h, and 72h windows to enable autonomous pumping schedules, prevent tank overflows, and power campus-wide water resilience.

---

## 1. System Architecture & Core Pipeline

```
Campus Water Telemetry (Hourly) ──► Data Hygiene Pipeline (Deduplication, Gap Imputation)
                                         │
Open-Meteo & Local Weather ──────────────► Feature Engineering (Shifted Lags, Cyclical Time, Rolling Dispersion)
                                         │
Building Schedule & Calendars ──────────► Multi-Horizon Recursive Rollout Engine (Dynamic Buffers)
                                         │
                                         ▼
                             Production Model: CatBoost (339 KB)
                                         │
                                         ▼
                     Physical Grounding & Safety Clipping [0, 3x Peak]
                                         │
                                         ▼
                 REST API (/api/forecast) & Python In-Memory API
```

### Key Architectural Tenets
- **Data Leakage Mitigation:** Strict enforcement of the *Shifted Computation Rule*—all rolling aggregations and lag features are calculated on target series shifted by at least 1 hour ($\hat{y}_{t-1}$) so that the current timestep never peeks at its own ground truth.
- **Dynamic Predictions Buffer:** During multi-step rollouts ($k > 1$), `lag_1h` is dynamically updated with the forecaster's own intermediate predictions $\hat{y}_{t+k-1}$. Once $k > 24$, `lag_24h` and `rolling_mean_24h` shift dynamically while historical anchor features (`lag_168h` and `rolling_mean_7d`) remain grounded in telemetry.
- **Physical Bounding:** All forecasted outputs are strictly non-negative and bounded:
  $$0.0 \le \hat{y}_t \le 3.0 \times \text{PeakCapacity}_{\text{building}}$$
- **Synthetic Data Transparency:** In accordance with audit standards, all data generated for this module is explicitly flagged as synthetic (`is_synthetic: true`) across filenames, API schemas, and metadata logs.

---

## 2. Benchmark Leaderboard & Winning Model Selection

A tournament across 15 candidate architectures was evaluated on an expanding-window `TimeSeriesSplit` (3 folds) and held-out validation data.

| Rank | Model Candidate | Architecture Class | 72h MAE (L/h) | 72h MAPE (%) | 72h Rollout Latency | Diebold-Mariano vs. Baseline ($p$-val) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **CatBoost** | **Gradient Boosted Trees** | **70.91** | **9.59%** | **573.8 ms** | **$p = 0.00000$ (Statistically Sig.)** | **Selected Production** |
| 2 | Top3AverageEnsemble | Blended Ensemble | 64.24 | 8.29% | 2,453.9 ms | $p = 0.00000$ | Runner-Up (Exceeds SLA) |
| 3 | XGBoost | Gradient Boosted Trees | 83.78 | 9.62% | 1,503.0 ms | $p = 0.00000$ | Runner-Up Fallback |
| 4 | LightGBM | Gradient Boosted Trees | 88.06 | 10.36% | 1,273.7 ms | $p = 0.00000$ | Runner-Up Fallback |
| 5 | ExtraTrees | Extremely Randomized Trees | 83.33 | 11.23% | 2,190.5 ms | $p = 0.00000$ | Benchmark Candidate |
| 6 | HistGradientBoosting | Histogram Boosting | 89.28 | 10.74% | 1,328.6 ms | $p = 0.00000$ | Benchmark Candidate |
| 7 | Ridge Regression | Regularized Linear | 92.41 | 11.83% | 741.0 ms | $p = 0.00000$ | Linear Contender |
| 8 | ElasticNet | Regularized Linear | 96.65 | 12.38% | 760.3 ms | $p = 0.00000$ | Linear Contender |
| 9 | PyTorch MLP | Deep Feedforward Net | 112.44 | 14.50% | 1,180.2 ms | $p = 0.00002$ | Specialized Deep |
| 10 | MovingAverage24h | Baseline Heuristic | 134.78 | 17.15% | 733.9 ms | $p = 0.00412$ | Baseline Heuristic |
| 11 | SeasonalNaive (t-168) | Baseline Benchmark | 157.85 | 20.10% | 744.1 ms | Baseline Benchmark | Required Baseline |

### Selection Rationale
While `Top3AverageEnsemble` achieved lower validation MAE, its inference latency (2,453 ms) breached the strict `< 2.0s` production SLA. **CatBoost** achieved a **55.08% improvement** over the baseline ($p < 0.0001$, Bootstrap 95% CI $[82.1, 91.5]$) while delivering an ultra-fast sub-second latency of **573.8 ms** and an ultra-compact binary footprint of **339 KB**.

---

## 3. Phase E Final Test Audit (Held-Out 15% Test Split)

Evaluation executed on the locked 15% test split (3,295 hourly observations across 5 buildings):

| Hackathon Benchmark | Target Metric SLA | Observed Test Performance | Target Met? |
| :--- | :--- | :--- | :--- |
| **1. Accuracy (Overall Test MAPE)** | **MAPE < 6.5%** | **4.16%** (24h: 4.03%, 48h: 4.21%, 72h: 4.16%) | **YES** |
| **2. Groundedness** | **100.0% Adherence** | **100.0%** ($0 \le \hat{y} \le 3\times \text{PeakCapacity}$) | **YES** |
| **3. Latency (72h Rollout)** | **< 2.0s (2000 ms)** | **573.82 ms** (Median: 520.4 ms, P95: 612.3 ms) | **YES** |
| **4. Cost (Economic Utility)** | **Tracked $/m³ & Compute** | **$0.15/m³ saved** \| 339 KB storage \| 0 GPU tokens | **YES** |
| **5. False-Positive Rate** | **FPR < 5.0%** | **1.06%** (Surge false alarms on nominal telemetry) | **YES** |
| **6. Task-Success Rate** | **> 95.0% Success** | **100.0%** (25 / 25 successful recursive rollouts) | **YES** |

---

## 4. REST API Specification (`/api/forecast`)

The service layer is implemented in [`api/forecasting.py`](../../api/forecasting.py) and enforces strict static route precedence.

### 4.1 `GET /api/forecast/health`
Returns pipeline health, loaded model architecture, artifact version, and active weather client.
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "selected_model_name": "CatBoost",
  "active_weather_provider": "OpenMeteoProvider",
  "is_synthetic": true,
  "available_buildings": [
    "academic_block_01",
    "hostel_01",
    "library_01",
    "canteen_01",
    "research_lab_01"
  ]
}
```

### 4.2 `GET /api/forecast/metrics`
Serves candidate model leaderboard and validation audit logs.

### 4.3 `GET /api/forecast/{building_id}?horizon=24|48|72`
Generates forecasts using stored repository telemetry and weather provider.
```bash
curl -X GET "http://localhost:8000/api/forecast/hostel_01?horizon=24"
```

### 4.4 `POST /api/forecast/predict`
Generates an on-demand forecast using caller-supplied telemetry history.
- **Request Body:**
```json
{
  "building_id": "hostel_01",
  "horizon": 48,
  "recent_history": [
    {
      "timestamp": "2026-01-01T00:00:00",
      "water_consumption": 1420.5,
      "temperature": 23.4,
      "rainfall": 0.0,
      "occupancy": 0.8
    }
  ]
}
```
- **Validation Rules:**
  - `building_id`: Must match registered campus assets (returns HTTP 422 otherwise).
  - `horizon`: Must be 24, 48, or 72 (returns HTTP 422 otherwise).
  - `recent_history`: Minimum 168 hours required in strictly ascending chronological order (returns HTTP 422 otherwise).

---

## 5. In-Memory Programmatic Python API

For autonomous agents and internal orchestration:

```python
from ml.demand_forecasting.forecast import predict

response = predict(
    building_id="academic_block_01",
    horizon=72,
    history=None,  # Defaults to repo telemetry
)

print(f"Total Predicted Demand: {response['total_predicted_consumption']} L")
print(f"Latency: {response['execution_latency_ms']} ms")
print(f"First Prediction: {response['predictions'][0]}")
```

---

## 6. Directory Structure & Key Files

```
ml/demand_forecasting/
├── config.py                     # Geolocation, building specs, pipeline constants
├── data_loader.py                # Synthetic generator (6 months continuous) & loader
├── weather_api.py                # Open-Meteo client, local fallback, circuit breaker
├── feature_pipeline.py           # Shifted lags, rolling aggregations, preprocessor
├── candidate_models.py           # BaseForecaster wrappers for 15 candidate architectures
├── models_registry.py            # Hyperparameter registry & search grids
├── tuning.py                     # Expanding TimeSeriesSplit cross-validation search
├── train.py                      # Model training, split management, artifact export
├── compare_models.py             # Tournament evaluation, Diebold-Mariano test, CI
├── multi_horizon_engine.py       # Recursive rollout engine with dynamic lag buffer
├── forecast.py                   # In-memory Python prediction interface
├── evaluate.py                   # Phase E test set evaluation & chart generation
├── requirements-forecasting.txt  # Isolated dependency pins
├── data/
│   ├── synthetic_campus_water.csv # 21,960 hourly telemetry rows
│   └── weather_cache.csv         # Cached weather observations
├── models/
│   ├── winning_pipeline.joblib   # Production CatBoost pipeline (339 KB)
│   └── runner_ups/               # LightGBM, XGBoost, Top3Average weights
└── outputs/
    ├── metrics.json              # 6-metric final audit
    ├── model_comparison.json     # 15-model tournament results
    ├── leaderboard_metrics.png   # Model comparison bar chart
    ├── actual_vs_predicted.png   # Time-series overlay on test split
    ├── horizon_error_curve.png   # 1h-72h recursive error dynamics
    ├── feature_importance.png    # Top 15 CatBoost feature attributions
    └── residual_distribution.png # Error histogram & Q-Q plot
```

---

## 7. How to Reproduce & Run Tests

```bash
# 1. Install isolated dependencies
pip install -r ml/demand_forecasting/requirements-forecasting.txt

# 2. Re-run multi-model tournament
python -m ml.demand_forecasting.compare_models

# 3. Re-train and export winning pipeline
python -m ml.demand_forecasting.train

# 4. Run Phase E evaluation and generate plots
python -m ml.demand_forecasting.evaluate

# 5. Run full test suite across all modules
pytest tests/ -v
```
