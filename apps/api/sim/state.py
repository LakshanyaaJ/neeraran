from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WeatherState(BaseModel):
    temp_c: float = 29.5
    condition: str = "Partly Cloudy"
    rainfall_mm: float = 0.0
    humidity_pct: float = 68.0
    forecast_rain_prob_pct: float = 15.0

class BlockState(BaseModel):
    id: str
    name: str
    code: str
    category: str # "residential", "academic", "utility", "health", "sports", "admin"
    population: int
    is_vulnerable: bool
    fed_by_tank_id: str
    coordinates: List[float] # [lng, lat]
    baseline_demand_lpm: float # Litres per min
    current_demand_lpm: float
    current_pressure_bar: float
    status: str = "normal" # "normal", "watch", "critical"

class TankState(BaseModel):
    id: str
    name: str
    capacity_kl: float
    current_level_kl: float
    pct_full: float
    inflow_lpm: float
    outflow_lpm: float
    status: str = "normal" # "normal", "watch", "critical"
    fed_by_pump: str
    serves_blocks: List[str]

class BorewellState(BaseModel):
    id: str
    name: str
    depth_m: float
    max_yield_lpm: float
    current_flow_lpm: float
    pump_status: str = "running" # "running", "idle", "fault"
    power_kw: float
    water_table_depth_m: float

class SumpState(BaseModel):
    id: str = "SUMP-MAIN"
    name: str = "Central Campus Utility Sump"
    capacity_kl: float = 500.0
    current_level_kl: float = 385.0
    pct_full: float = 77.0
    raw_inflow_lpm: float = 420.0
    pump_outflow_lpm: float = 390.0
    status: str = "normal"

class STPState(BaseModel):
    id: str = "STP-MAIN"
    name: str = "Campus Greywater Reclamation Plant"
    capacity_kld: float = 150.0
    current_inflow_kld: float = 118.5
    treated_outflow_kld: float = 112.0
    reuse_rate_pct: float = 94.5
    recycled_to_turf_kld: float = 65.0
    recycled_to_cooling_kld: float = 47.0

class PipeSegmentState(BaseModel):
    id: str
    from_node: str
    to_node: str
    diameter_mm: int
    length_m: float
    flow_lpm: float
    pressure_bar: float
    leak_rate_lpm: float = 0.0
    is_leaking: bool = False
    coordinates: List[List[float]] # GeoJSON line string [[lng, lat], ...]

class SimulationState(BaseModel):
    sim_time_iso: str
    sim_day_name: str
    hour_of_day: float
    tick: int
    speed: int
    is_paused: bool
    seed: int
    weather: WeatherState
    sump: SumpState
    tanks: List[TankState]
    borewells: List[BorewellState]
    stp: STPState
    blocks: List[BlockState]
    pipes: List[PipeSegmentState]
    total_consumption_lpm: float
    total_inflow_lpm: float
    net_storage_kl: float
    storage_reserve_hours: float
    active_leaks_count: int
    active_alerts: List[Dict[str, Any]] = Field(default_factory=list)
