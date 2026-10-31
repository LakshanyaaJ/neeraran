"""AquaMind AI - Weather Provider Integration.

Provides abstract WeatherProvider interface and pluggable OpenMeteoProvider
with exponential backoff, strict 3.0s timeout, and seamless fallback to LocalFileWeatherProvider.
Zero unmocked external network calls allowed during automated testing.
"""

import abc
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd

from ml.demand_forecasting.config import PATHS, WEATHER

logger = logging.getLogger(__name__)


class WeatherProvider(abc.ABC):
    """Abstract interface for weather providers."""

    @abc.abstractmethod
    def get_forecast(
        self,
        hours: int = 72,
        start_time: Optional[datetime] = None,
    ) -> Tuple[pd.DataFrame, str]:
        """Fetches future hourly temperature and rainfall predictions.
        
        Returns:
            Tuple of (DataFrame with [timestamp, temperature, rainfall], weather_source string).
        """
        pass

    @abc.abstractmethod
    def get_historical(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Tuple[pd.DataFrame, str]:
        """Fetches past hourly temperature and rainfall observations.
        
        Returns:
            Tuple of (DataFrame with [timestamp, temperature, rainfall], weather_source string).
        """
        pass


class LocalFileWeatherProvider(WeatherProvider):
    """Offline resilient weather provider reading from pre-fetched local CSV cache."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = Path(cache_path) if cache_path else PATHS.WEATHER_CACHE_PATH
        self._cache_df: Optional[pd.DataFrame] = None

    def _load_cache(self) -> pd.DataFrame:
        if self._cache_df is None:
            if not self.cache_path.exists():
                # Generate synthetic fallback if cache file doesn't exist
                from ml.demand_forecasting.data_loader import generate_synthetic_dataset
                _, df_w = generate_synthetic_dataset(save_to_disk=True)
                self._cache_df = df_w
            else:
                df = pd.read_csv(self.cache_path)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                self._cache_df = df
        return self._cache_df

    def get_forecast(
        self,
        hours: int = 72,
        start_time: Optional[datetime] = None,
    ) -> Tuple[pd.DataFrame, str]:
        df = self._load_cache()
        if start_time is None:
            start_dt = df["timestamp"].min()
        else:
            start_dt = pd.to_datetime(start_time)
            if start_dt.tzinfo is not None:
                start_dt = start_dt.tz_convert(None)

        filtered = df[df["timestamp"] >= start_dt].sort_values("timestamp")
        if len(filtered) < hours:
            # Wrap around or extrapolate realistically
            last_dt = filtered["timestamp"].iloc[-1] if not filtered.empty else start_dt
            needed = hours - len(filtered)
            extra_timestamps = pd.date_range(start=last_dt + pd.Timedelta(hours=1), periods=needed, freq="h")
            # Baseline mean temperature 26°C with daily variation
            extra_temp = 26.0 + 4.0 * np.sin(2 * np.pi * (extra_timestamps.hour - 8) / 24)
            extra_rain = np.zeros(needed)
            extra_df = pd.DataFrame({
                "timestamp": extra_timestamps,
                "temperature": np.round(extra_temp, 1),
                "rainfall": extra_rain,
            })
            result = pd.concat([filtered, extra_df], ignore_index=True)
        else:
            result = filtered.iloc[:hours].copy()

        return result[["timestamp", "temperature", "rainfall"]].reset_index(drop=True), "local"

    def get_historical(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Tuple[pd.DataFrame, str]:
        df = self._load_cache()
        s_dt = pd.to_datetime(start_time)
        e_dt = pd.to_datetime(end_time)
        if s_dt.tzinfo is not None:
            s_dt = s_dt.tz_convert(None)
        if e_dt.tzinfo is not None:
            e_dt = e_dt.tz_convert(None)

        mask = (df["timestamp"] >= s_dt) & (df["timestamp"] <= e_dt)
        filtered = df[mask].sort_values("timestamp")
        return filtered[["timestamp", "temperature", "rainfall"]].reset_index(drop=True), "local"


class OpenMeteoProvider(WeatherProvider):
    """Live weather provider calling Open-Meteo REST endpoints with retry and local fallback."""

    def __init__(
        self,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: float = WEATHER.TIMEOUT_SECONDS,
        max_retries: int = WEATHER.MAX_RETRIES,
        backoff_factor: float = WEATHER.BACKOFF_FACTOR,
        fallback_provider: Optional[WeatherProvider] = None,
    ):
        self.transport = transport
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.fallback = fallback_provider or LocalFileWeatherProvider()
        self._memory_cache: Dict[str, Tuple[float, pd.DataFrame]] = {}
        self._cache_ttl_sec = 300.0  # 5 minutes in-memory cache
        self._offline_until: float = 0.0
        self._offline_cooldown_sec: float = 60.0

    def _execute_request_with_retry(self, url: str, params: Dict) -> dict:
        """Executes GET request with exponential backoff and timeout."""
        last_exc: Optional[Exception] = None
        
        with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = client.get(url, params=params)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.warning(
                            f"OpenMeteo returned status {response.status_code} on attempt {attempt}"
                        )
                except (httpx.TimeoutException, httpx.RequestError) as exc:
                    last_exc = exc
                    logger.warning(f"OpenMeteo attempt {attempt} failed: {exc}")
                    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout)):
                        # Network is completely unreachable or DNS resolution failed:
                        # Trip offline circuit breaker and failover immediately without burning retry sleep
                        self._offline_until = time.time() + self._offline_cooldown_sec
                        break

                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2 ** (attempt - 1))
                    time.sleep(sleep_time)

        raise RuntimeError(f"Open-Meteo API failed after {self.max_retries} attempts: {last_exc}")

    def get_forecast(
        self,
        hours: int = 72,
        start_time: Optional[datetime] = None,
    ) -> Tuple[pd.DataFrame, str]:
        if time.time() < self._offline_until:
            df_fallback, _ = self.fallback.get_forecast(hours, start_time)
            return df_fallback, "local"

        cache_key = f"forecast_{hours}_{start_time}"
        now_ts = time.time()
        
        if cache_key in self._memory_cache:
            saved_time, cached_df = self._memory_cache[cache_key]
            if now_ts - saved_time < self._cache_ttl_sec:
                return cached_df.copy(), "cache"

        params = {
            "latitude": WEATHER.LATITUDE,
            "longitude": WEATHER.LONGITUDE,
            "hourly": "temperature_2m,precipitation",
            "timezone": WEATHER.TIMEZONE,
            "forecast_days": max(1, int(np.ceil(hours / 24.0))),
        }

        try:
            data = self._execute_request_with_retry(WEATHER.FORECAST_ENDPOINT, params)
            hourly = data.get("hourly", {})
            times = pd.to_datetime(hourly.get("time", []))
            temps = hourly.get("temperature_2m", [])
            rain = hourly.get("precipitation", [])

            df = pd.DataFrame({
                "timestamp": times,
                "temperature": [float(t) if t is not None else 25.0 for t in temps],
                "rainfall": [float(r) if r is not None else 0.0 for r in rain],
            })
            
            if start_time is not None:
                st = pd.to_datetime(start_time)
                if st.tzinfo is not None:
                    st = st.tz_convert(None)
                df = df[df["timestamp"] >= st]

            df = df.iloc[:hours].reset_index(drop=True)
            self._memory_cache[cache_key] = (now_ts, df.copy())
            return df, "open-meteo"

        except Exception as exc:
            logger.warning(f"Falling back to LocalFileWeatherProvider due to: {exc}")
            df_fallback, _ = self.fallback.get_forecast(hours, start_time)
            return df_fallback, "local"

    def get_historical(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Tuple[pd.DataFrame, str]:
        if time.time() < self._offline_until:
            df_fallback, _ = self.fallback.get_historical(start_time, end_time)
            return df_fallback, "local"

        s_str = start_time.strftime("%Y-%m-%d")
        e_str = end_time.strftime("%Y-%m-%d")
        cache_key = f"hist_{s_str}_{e_str}"
        now_ts = time.time()

        if cache_key in self._memory_cache:
            saved_time, cached_df = self._memory_cache[cache_key]
            if now_ts - saved_time < self._cache_ttl_sec:
                return cached_df.copy(), "cache"

        params = {
            "latitude": WEATHER.LATITUDE,
            "longitude": WEATHER.LONGITUDE,
            "start_date": s_str,
            "end_date": e_str,
            "hourly": "temperature_2m,precipitation",
            "timezone": WEATHER.TIMEZONE,
        }

        try:
            data = self._execute_request_with_retry(WEATHER.ARCHIVE_ENDPOINT, params)
            hourly = data.get("hourly", {})
            times = pd.to_datetime(hourly.get("time", []))
            temps = hourly.get("temperature_2m", [])
            rain = hourly.get("precipitation", [])

            df = pd.DataFrame({
                "timestamp": times,
                "temperature": [float(t) if t is not None else 25.0 for t in temps],
                "rainfall": [float(r) if r is not None else 0.0 for r in rain],
            })
            self._memory_cache[cache_key] = (now_ts, df.copy())
            return df, "open-meteo"

        except Exception as exc:
            logger.warning(f"Falling back to LocalFileWeatherProvider for archive due to: {exc}")
            df_fallback, _ = self.fallback.get_historical(start_time, end_time)
            return df_fallback, "local"


def get_default_weather_provider(transport: Optional[httpx.BaseTransport] = None) -> WeatherProvider:
    """Factory creating configured OpenMeteoProvider with offline fallback."""
    return OpenMeteoProvider(transport=transport)
