"""Unit and Integration Tests for Phase D - FastAPI Service Layer.

Verifies:
1. Static route precedence (confirming /health and /metrics are never captured by /{building_id}).
2. GET /api/forecast/{building_id} across multi-horizon windows (24h, 48h, 72h).
3. POST /api/forecast/predict with valid payloads and custom history buffers.
4. HTTP 422 Unprocessable Entity responses on invalid building IDs, unsupported horizons,
   insufficient history (< 168 hours), and non-ascending timestamp sequences.
5. Mock weather provider integration during API request execution.
"""

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.forecasting import app, set_weather_provider
from ml.demand_forecasting.config import BUILDINGS
from ml.demand_forecasting.data_loader import generate_synthetic_dataset
from ml.demand_forecasting.weather_api import WeatherProvider


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance bound to the FastAPI forecasting app."""
    return TestClient(app)


@pytest.fixture(scope="module")
def valid_168h_history():
    """Generates 168 hours (1 full week) of continuous hourly telemetry."""
    base_time = datetime(2026, 1, 1, 0, 0, 0)
    history = []
    for h in range(168):
        ts = base_time + timedelta(hours=h)
        history.append({
            "timestamp": ts.isoformat(),
            "water_consumption": 1200.0 + (h % 24) * 30.0,
            "temperature": 24.0 + (h % 24) * 0.5,
            "rainfall": 0.0,
            "occupancy": 0.75,
        })
    return history


class MockCustomWeatherProvider(WeatherProvider):
    """Mock weather provider returning constant test weather."""

    def __init__(self, temp: float = 38.5, rain: float = 12.0):
        self.temp = temp
        self.rain = rain

    def get_forecast(
        self, hours: int = 72, start_time: Optional[datetime] = None
    ) -> Tuple[pd.DataFrame, str]:
        st = pd.to_datetime(start_time or datetime.now())
        timestamps = [st + timedelta(hours=i) for i in range(hours)]
        df = pd.DataFrame({
            "timestamp": timestamps,
            "temperature": [self.temp] * hours,
            "rainfall": [self.rain] * hours,
        })
        return df, "mock-test-weather"

    def get_historical(
        self, start_time: datetime, end_time: datetime
    ) -> Tuple[pd.DataFrame, str]:
        timestamps = pd.date_range(start_time, end_time, freq="h")
        df = pd.DataFrame({
            "timestamp": timestamps,
            "temperature": [self.temp] * len(timestamps),
            "rainfall": [self.rain] * len(timestamps),
        })
        return df, "mock-test-weather"


class TestStaticRoutePrecedence:
    """Verifies that static paths are never swallowed by the /{building_id} path parameter."""

    def test_health_endpoint_precedence(self, client):
        response = client.get("/api/forecast/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["model_version"] == "v1.0.0"
        assert data["selected_model_name"] == "CatBoost"
        assert "available_buildings" in data
        assert "hostel_01" in data["available_buildings"]
        # Ensure 'health' was not interpreted as a building_id
        assert "predictions" not in data

    def test_metrics_endpoint_precedence(self, client):
        response = client.get("/api/forecast/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["is_synthetic"] is True
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)
        assert len(data["leaderboard"]) > 0
        # Ensure 'metrics' was not interpreted as a building_id
        assert "predictions" not in data


class TestGetBuildingForecast:
    """Tests GET /api/forecast/{building_id} with query parameters."""

    @pytest.mark.parametrize("horizon", [24, 48, 72])
    def test_multi_horizon_get_forecast(self, client, horizon):
        building_id = "hostel_01"
        response = client.get(f"/api/forecast/{building_id}?horizon={horizon}")
        assert response.status_code == 200
        data = response.json()

        assert data["building_id"] == building_id
        assert data["horizon_hours"] == horizon
        assert data["unit"] == "litres"
        assert data["is_synthetic"] is True
        assert len(data["predictions"]) == horizon
        assert data["total_predicted_consumption"] > 0
        assert data["peak_predicted_consumption"] >= data["min_predicted_consumption"]
        assert data["execution_latency_ms"] > 0

        # Verify hourly timestamp continuity and non-negativity
        predictions = data["predictions"]
        for p in predictions:
            assert p["predicted_consumption"] >= 0.0

        ts_list = [pd.to_datetime(p["timestamp"]) for p in predictions]
        for i in range(1, len(ts_list)):
            assert ts_list[i] - ts_list[i - 1] == timedelta(hours=1)

    def test_all_campus_buildings_supported(self, client):
        for b_id in BUILDINGS.BUILDINGS.keys():
            response = client.get(f"/api/forecast/{b_id}?horizon=24")
            assert response.status_code == 200
            data = response.json()
            assert data["building_id"] == b_id
            assert len(data["predictions"]) == 24


class TestPostPredictEndpoint:
    """Tests POST /api/forecast/predict with user-supplied history."""

    def test_post_predict_valid_payload(self, client, valid_168h_history):
        payload = {
            "building_id": "academic_block_01",
            "horizon": 48,
            "recent_history": valid_168h_history,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["building_id"] == "academic_block_01"
        assert data["horizon_hours"] == 48
        assert len(data["predictions"]) == 48
        assert data["total_predicted_consumption"] > 0

    def test_post_predict_omitted_history_uses_repository(self, client):
        payload = {
            "building_id": "canteen_01",
            "horizon": 24,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["building_id"] == "canteen_01"
        assert len(data["predictions"]) == 24


class TestValidationErrorHandlers:
    """Verifies that invalid requests return HTTP 422 Unprocessable Entity."""

    def test_get_unknown_building_id(self, client):
        response = client.get("/api/forecast/unknown_building_xyz?horizon=24")
        assert response.status_code == 422
        assert "Unknown building_id" in response.json()["detail"]

    def test_get_unsupported_horizon(self, client):
        response = client.get("/api/forecast/hostel_01?horizon=12")
        assert response.status_code == 422
        assert "Invalid horizon" in response.json()["detail"]

    def test_post_unknown_building_id(self, client):
        payload = {
            "building_id": "invalid_building_001",
            "horizon": 24,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 422

    def test_post_unsupported_horizon(self, client):
        payload = {
            "building_id": "library_01",
            "horizon": 36,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 422

    def test_post_insufficient_history_length(self, client, valid_168h_history):
        # Only 50 hours instead of the mandatory 168 hours
        short_history = valid_168h_history[:50]
        payload = {
            "building_id": "research_lab_01",
            "horizon": 24,
            "recent_history": short_history,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 422
        assert "minimum 168 hours" in str(response.json())

    def test_post_non_ascending_timestamps(self, client, valid_168h_history):
        # Introduce a descending timestamp inversion
        scrambled_history = [dict(item) for item in valid_168h_history]
        scrambled_history[10]["timestamp"] = scrambled_history[5]["timestamp"]

        payload = {
            "building_id": "hostel_01",
            "horizon": 24,
            "recent_history": scrambled_history,
        }
        response = client.post("/api/forecast/predict", json=payload)
        assert response.status_code == 422
        assert "chronological" in str(response.json()).lower()


class TestMockWeatherIntegration:
    """Verifies that custom/mock weather providers integrate seamlessly."""

    def test_mock_weather_provider_injection(self, client):
        mock_provider = MockCustomWeatherProvider(temp=41.2, rain=15.0)
        try:
            set_weather_provider(mock_provider)
            response = client.get("/api/forecast/hostel_01?horizon=24")
            assert response.status_code == 200
            data = response.json()
            assert data["weather_source"] == "mock-test-weather"
        finally:
            set_weather_provider(None)
