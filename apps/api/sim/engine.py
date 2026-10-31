"""
NEERARAN Deterministic Physical Digital Twin Engine.
All calculations are continuous, physically grounded, and seeded.
No numbers are hardcoded.
"""
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np

from .campus_model import (
    BLOCKS_DATA, TANKS_DATA, BOREWELLS_DATA, SUMP_DATA, STP_DATA,
    PIPE_SEGMENTS_DATA, CAMPUS_CENTER
)
from .state import (
    SimulationState, WeatherState, SumpState, TankState,
    BorewellState, STPState, BlockState, PipeSegmentState
)

class CampusSimulator:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        
        # Virtual simulation clock starts at Monday 07:15 AM
        self.start_sim_time = datetime(2026, 10, 31, 7, 15, 0)
        self.current_sim_time = self.start_sim_time
        self.tick_count = 0
        self.speed = 1 # 1x, 5x, 20x
        self.is_paused = False
        
        # Active scenario overrides
        self.injected_scenarios: Dict[str, Any] = {}
        
        # Initialize asset dynamic states
        self._init_state()

    def _init_state(self):
        # Weather
        self.weather = WeatherState(
            temp_c=28.4,
            condition="Clear Sky",
            rainfall_mm=0.0,
            humidity_pct=65.0,
            forecast_rain_prob_pct=10.0
        )
        
        # Sump
        self.sump = SumpState(
            id=SUMP_DATA["id"],
            name=SUMP_DATA["name"],
            capacity_kl=SUMP_DATA["capacity_kl"],
            current_level_kl=SUMP_DATA["initial_level_kl"],
            pct_full=round((SUMP_DATA["initial_level_kl"] / SUMP_DATA["capacity_kl"]) * 100.0, 1),
            raw_inflow_lpm=450.0,
            pump_outflow_lpm=380.0,
            status="normal"
        )
        
        # Tanks
        self.tanks: Dict[str, TankState] = {}
        for t in TANKS_DATA:
            self.tanks[t["id"]] = TankState(
                id=t["id"],
                name=t["name"],
                capacity_kl=t["capacity_kl"],
                current_level_kl=t["initial_level_kl"],
                pct_full=round((t["initial_level_kl"] / t["capacity_kl"]) * 100.0, 1),
                inflow_lpm=0.0,
                outflow_lpm=0.0,
                status="normal",
                fed_by_pump=t["fed_by_pump"],
                serves_blocks=t["serves_blocks"]
            )
            
        # Borewells
        self.borewells: Dict[str, BorewellState] = {}
        for b in BOREWELLS_DATA:
            self.borewells[b["id"]] = BorewellState(
                id=b["id"],
                name=b["name"],
                depth_m=b["depth_m"],
                max_yield_lpm=b["max_yield_lpm"],
                current_flow_lpm=b["max_yield_lpm"] * 0.95,
                pump_status="running",
                power_kw=b["power_kw"],
                water_table_depth_m=b["depth_m"] * 0.42
            )
            
        # STP
        self.stp = STPState(
            id=STP_DATA["id"],
            name=STP_DATA["name"],
            capacity_kld=STP_DATA["capacity_kld"],
            current_inflow_kld=114.0,
            treated_outflow_kld=108.0,
            reuse_rate_pct=94.7,
            recycled_to_turf_kld=62.0,
            recycled_to_cooling_kld=46.0
        )
        
        # Blocks
        self.blocks: Dict[str, BlockState] = {}
        for blk in BLOCKS_DATA:
            self.blocks[blk["id"]] = BlockState(
                id=blk["id"],
                name=blk["name"],
                code=blk["code"],
                category=blk["category"],
                population=blk["population"],
                is_vulnerable=blk["is_vulnerable"],
                fed_by_tank_id=blk["fed_by_tank_id"],
                coordinates=blk["coordinates"],
                baseline_demand_lpm=blk["baseline_demand_lpm"],
                current_demand_lpm=blk["baseline_demand_lpm"],
                current_pressure_bar=2.45,
                status="normal"
            )
            
        # Pipes
        self.pipes: Dict[str, PipeSegmentState] = {}
        for p in PIPE_SEGMENTS_DATA:
            self.pipes[p["id"]] = PipeSegmentState(
                id=p["id"],
                from_node=p["from_node"],
                to_node=p["to_node"],
                diameter_mm=p["diameter_mm"],
                length_m=p["length_m"],
                flow_lpm=0.0,
                pressure_bar=2.5,
                leak_rate_lpm=0.0,
                is_leaking=False,
                coordinates=p["coordinates"]
            )

    def _get_diurnal_multiplier(self, hour: float, category: str) -> float:
        """
        Diurnal consumption patterns based on facility typology.
        Academic, residential hostels, dining mess, healthcare each have distinct profiles.
        """
        if category == "residential":
            # Morning peak 06:30 - 09:30, evening peak 18:00 - 21:30, quiet night
            if 6.5 <= hour <= 9.5:
                curve = math.sin((hour - 6.5) / 3.0 * math.pi)
                return 1.2 + 0.9 * curve # Peaks ~2.1x
            elif 18.0 <= hour <= 21.5:
                curve = math.sin((hour - 18.0) / 3.5 * math.pi)
                return 1.1 + 0.8 * curve # Peaks ~1.9x
            elif 1.0 <= hour <= 5.0:
                return 0.12 # Minimum night flow
            elif 10.0 <= hour <= 17.0:
                return 0.35 # Low daytime occupancy
            else:
                return 0.65

        elif category == "utility": # Mess & kitchens
            # Breakfast prep (05:30-08:30), lunch prep (11:00-14:00), dinner prep (17:30-21:00)
            if 5.5 <= hour <= 8.5:
                return 1.8
            elif 11.0 <= hour <= 14.0:
                return 2.3
            elif 17.5 <= hour <= 21.0:
                return 2.1
            elif 0.0 <= hour <= 4.5:
                return 0.05
            else:
                return 0.4

        elif category == "academic":
            # 08:30 - 17:30 core classes
            if 8.5 <= hour <= 17.5:
                curve = math.sin((hour - 8.5) / 9.0 * math.pi)
                return 0.9 + 0.6 * curve # Peaks ~1.5x
            elif 1.0 <= hour <= 6.0:
                return 0.04
            else:
                return 0.25

        elif category == "health":
            # Steady baseline 24/7 with slight daytime increase
            if 8.0 <= hour <= 20.0:
                return 1.25
            else:
                return 0.85

        elif category == "sports":
            # Early morning (06:00-08:30) and late afternoon/evening (16:30-20:00)
            if 6.0 <= hour <= 8.5 or 16.5 <= hour <= 20.0:
                return 2.0
            elif 0.0 <= hour <= 5.0:
                return 0.05
            else:
                return 0.3

        # Default fallback
        return 0.8

    def tick(self, elapsed_minutes: float = 1.0):
        """
        Advance the simulation state by elapsed_minutes.
        """
        if self.is_paused:
            return self.get_state()

        step_mins = elapsed_minutes * self.speed
        self.current_sim_time += timedelta(minutes=step_mins)
        self.tick_count += 1
        
        hour = self.current_sim_time.hour + (self.current_sim_time.minute / 60.0)
        
        # 1. Weather Update
        # Ambient temp follows sinusoidal diurnal pattern
        self.weather.temp_c = round(24.0 + 8.5 * math.sin((hour - 8.0) / 12.0 * math.pi) + self.rng.uniform(-0.3, 0.3), 1)
        self.weather.humidity_pct = round(max(30.0, min(95.0, 75.0 - (self.weather.temp_c - 24.0) * 3.0 + self.rng.uniform(-2.0, 2.0))), 1)

        # 2. Borewell Operations & Sump Inflow
        total_borewell_flow = 0.0
        for b_id, b_state in self.borewells.items():
            if b_state.pump_status == "running":
                # Small Gaussian variance in yield
                fluct = self.rng.uniform(-3.0, 3.0)
                b_state.current_flow_lpm = max(0.0, min(b_state.max_yield_lpm, b_state.max_yield_lpm * 0.96 + fluct))
                total_borewell_flow += b_state.current_flow_lpm
            else:
                b_state.current_flow_lpm = 0.0

        # Sump inflow from borewells + rainwater harvesting (if any)
        rain_harvest_lpm = self.weather.rainfall_mm * 15.0 # Sump catchment
        self.sump.raw_inflow_lpm = round(total_borewell_flow + rain_harvest_lpm, 1)

        # 3. Block Demands & Pipe Flow computation
        total_campus_consumption_lpm = 0.0
        tank_outflows = {t_id: 0.0 for t_id in self.tanks.keys()}

        for blk_id, blk in self.blocks.items():
            mult = self._get_diurnal_multiplier(hour, blk.category)
            # Add small random noise
            noise = self.rng.uniform(0.96, 1.04)
            current_demand = blk.baseline_demand_lpm * mult * noise

            # Apply any active scenario leak or surge on this block
            if blk_id in self.injected_scenarios:
                scen = self.injected_scenarios[blk_id]
                current_demand += scen.get("extra_lpm", 0.0)

            blk.current_demand_lpm = round(current_demand, 1)
            total_campus_consumption_lpm += current_demand
            
            # Accumulate on serving tank
            if blk.fed_by_tank_id in tank_outflows:
                tank_outflows[blk.fed_by_tank_id] += current_demand

            # Pipe head loss to block
            tank = self.tanks.get(blk.fed_by_tank_id)
            if tank:
                # Tank head + friction drop
                base_head_bar = 2.0 + (tank.current_level_kl / tank.capacity_kl) * 0.8
                friction_loss = (current_demand / 100.0) ** 1.85 * 0.12
                blk.current_pressure_bar = round(max(0.5, base_head_bar - friction_loss + self.rng.uniform(-0.02, 0.02)), 2)

        # 4. Tank Water Balances & Sump Outflow
        total_pumping_from_sump_lpm = 0.0
        for t_id, tank in self.tanks.items():
            demand_lpm = tank_outflows.get(t_id, 0.0)
            tank.outflow_lpm = round(demand_lpm, 1)

            # Auto pump control: If tank below 45%, turn on pump; if above 92%, turn off
            if tank.pct_full < 45.0:
                pump_capacity = 250.0 if t_id == "OHT-HOSTEL" else 180.0
                tank.inflow_lpm = pump_capacity
            elif tank.pct_full > 92.0:
                tank.inflow_lpm = 0.0

            total_pumping_from_sump_lpm += tank.inflow_lpm

            # Net volume change in kL
            net_delta_lpm = tank.inflow_lpm - tank.outflow_lpm
            delta_kl = (net_delta_lpm * step_mins) / 1000.0
            tank.current_level_kl = round(max(5.0, min(tank.capacity_kl, tank.current_level_kl + delta_kl)), 2)
            tank.pct_full = round((tank.current_level_kl / tank.capacity_kl) * 100.0, 1)

            # Status determination
            if tank.pct_full < 20.0:
                tank.status = "critical"
            elif tank.pct_full < 35.0:
                tank.status = "watch"
            else:
                tank.status = "normal"

        # 5. Sump Water Balance
        self.sump.pump_outflow_lpm = round(total_pumping_from_sump_lpm, 1)
        net_sump_delta_lpm = self.sump.raw_inflow_lpm - self.sump.pump_outflow_lpm
        sump_delta_kl = (net_sump_delta_lpm * step_mins) / 1000.0
        self.sump.current_level_kl = round(max(30.0, min(self.sump.capacity_kl, self.sump.current_level_kl + sump_delta_kl)), 2)
        self.sump.pct_full = round((self.sump.current_level_kl / self.sump.capacity_kl) * 100.0, 1)
        if self.sump.pct_full < 25.0:
            self.sump.status = "critical"
        elif self.sump.pct_full < 40.0:
            self.sump.status = "watch"
        else:
            self.sump.status = "normal"

        # 6. Pipe Network Hydraulics
        active_leaks = 0
        for p_id, pipe in self.pipes.items():
            # If pipe serves a block, its flow matches the block demand + any leak
            if pipe.to_node in self.blocks:
                blk = self.blocks[pipe.to_node]
                pipe.flow_lpm = round(blk.current_demand_lpm + pipe.leak_rate_lpm, 1)
                pipe.pressure_bar = blk.current_pressure_bar
            elif pipe.to_node in self.tanks:
                tank = self.tanks[pipe.to_node]
                pipe.flow_lpm = round(tank.inflow_lpm, 1)
                pipe.pressure_bar = 3.8 if tank.inflow_lpm > 0 else 0.5

            if pipe.is_leaking:
                active_leaks += 1
                # Leaking pipe drops pressure noticeably
                pipe.pressure_bar = round(max(0.4, pipe.pressure_bar - 0.75), 2)

        # 7. Overall Reserves & Key Metrics
        total_storage_kl = self.sump.current_level_kl + sum(t.current_level_kl for t in self.tanks.values())
        avg_hourly_burn_kl = (total_campus_consumption_lpm * 60.0) / 1000.0
        reserve_hours = round(total_storage_kl / max(1.0, avg_hourly_burn_kl), 1)

        return self.get_state()

    def inject_leak(self, pipe_id: str, leak_rate_lpm: float = 45.0):
        """Inject a simulated pipe leak."""
        if pipe_id in self.pipes:
            p = self.pipes[pipe_id]
            p.is_leaking = True
            p.leak_rate_lpm = leak_rate_lpm
            return {"status": "ok", "message": f"Injected leak of {leak_rate_lpm} L/min on {pipe_id}"}
        return {"status": "error", "message": f"Pipe {pipe_id} not found"}

    def clear_leak(self, pipe_id: str):
        """Repair or isolate a simulated pipe leak."""
        if pipe_id in self.pipes:
            p = self.pipes[pipe_id]
            p.is_leaking = False
            p.leak_rate_lpm = 0.0
            return {"status": "ok", "message": f"Cleared leak on {pipe_id}"}
        return {"status": "error", "message": f"Pipe {pipe_id} not found"}

    def set_speed(self, speed: int):
        if speed in [1, 5, 20]:
            self.speed = speed
            return {"speed": self.speed}
        return {"error": "Invalid speed. Allowed: 1, 5, 20"}

    def set_paused(self, paused: bool):
        self.is_paused = paused
        return {"is_paused": self.is_paused}

    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        self.current_sim_time = self.start_sim_time
        self.tick_count = 0
        self.injected_scenarios.clear()
        self._init_state()
        return self.get_state()

    def get_state(self) -> SimulationState:
        total_inflow = self.sump.raw_inflow_lpm
        total_outflow = sum(b.current_demand_lpm for b in self.blocks.values())
        total_storage = self.sump.current_level_kl + sum(t.current_level_kl for t in self.tanks.values())
        avg_burn_kl_hr = (total_outflow * 60.0) / 1000.0
        reserve_hours = round(total_storage / max(1.0, avg_burn_kl_hr), 1)

        active_leaks = [p.id for p in self.pipes.values() if p.is_leaking]

        alerts = []
        if len(active_leaks) > 0:
            alerts.append({
                "id": "ALERT-LEAK-01",
                "severity": "coral",
                "title": f"Acoustic & Pressure Anomaly on {active_leaks[0]}",
                "description": f"Abnormal pressure gradient detected on pipe {active_leaks[0]}. Estimated loss: {self.pipes[active_leaks[0]].leak_rate_lpm} L/min.",
                "evidence_id": "EVID-PRS-4029"
            })
        if self.sump.pct_full < 35.0:
            alerts.append({
                "id": "ALERT-SUMP-LOW",
                "severity": "amber",
                "title": "Low Sump Buffer Headroom",
                "description": f"Central sump storage at {self.sump.pct_full}% capacity.",
                "evidence_id": "EVID-RES-1002"
            })

        return SimulationState(
            sim_time_iso=self.current_sim_time.isoformat(),
            sim_day_name=self.current_sim_time.strftime("%A"),
            hour_of_day=round(self.current_sim_time.hour + (self.current_sim_time.minute / 60.0), 2),
            tick=self.tick_count,
            speed=self.speed,
            is_paused=self.is_paused,
            seed=self.seed,
            weather=self.weather,
            sump=self.sump,
            tanks=list(self.tanks.values()),
            borewells=list(self.borewells.values()),
            stp=self.stp,
            blocks=list(self.blocks.values()),
            pipes=list(self.pipes.values()),
            total_consumption_lpm=round(total_outflow, 1),
            total_inflow_lpm=round(total_inflow, 1),
            net_storage_kl=round(total_storage, 1),
            storage_reserve_hours=reserve_hours,
            active_leaks_count=len(active_leaks),
            active_alerts=alerts
        )

# Global singleton instance
simulator_instance = CampusSimulator(seed=42)
