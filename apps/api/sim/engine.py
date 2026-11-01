"""
NEERARAN Deterministic Physical Digital Twin Engine — Phase 3
Full campus water physics with ground-truth fault injection.

Characteristics:
- 1 tick = 5 simulated minutes
- Seeded RNG (Random + NumPy) for 100% deterministic repeatability
- Realistic diurnal curves, weekend vs weekday, academic calendar occupancy
- Piezoresistive pressure drop on leaks and demand surges
- Tank levels in metres and kL from mass balance
- 72-hour weather forecast with error, ambient temperature
- Borewell yield with seasonal decline
- Lagged complaints generation from true faults
- Ground-truth table hidden from operational agents
"""
import math
import random
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
import numpy as np
from sqlmodel import Session, select

from ..db.database import (
    engine, Reading, GroundTruth, SystemEvent, ApprovalItem, AuditLog, CMMSTicket, get_utc_now
)

# Academic calendar constants
CALENDAR_SEMESTER = "semester"
CALENDAR_EXAM = "exam"
CALENDAR_VACATION = "vacation"

class CampusSimulatorPhase3:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        # Simulation clock starts on Monday, Aug 3, 2026 at 06:00 AM (Tick 0)
        self.base_time = datetime(2026, 8, 3, 6, 0, 0, tzinfo=timezone.utc)
        self.current_tick = 0
        self.speed = 1 # 1x, 5x, 20x
        self.is_paused = False

        # Load GeoJSON topology from /apps/api/data/campus.geojson
        with open("apps/api/data/campus.geojson", "r") as f:
            self.geojson = json.load(f)

        self._parse_topology()
        self._init_faults_and_ground_truth()
        self._init_state()

    def _parse_topology(self):
        self.blocks = {}
        self.tanks = {}
        self.borewells = {}
        self.pipes = {}
        self.sump = None
        self.muni_inlet = None
        self.stp = None

        for feat in self.geojson["features"]:
            props = feat["properties"]
            geom = feat["geometry"]
            f_type = props.get("type")

            if geom["type"] == "Polygon": # Campus Block
                self.blocks[props["id"]] = {
                    "id": props["id"],
                    "name": props["name"],
                    "code": props["code"],
                    "type": f_type,
                    "population": props["population"],
                    "vulnerable": props["vulnerable"],
                    "design_daily_demand_l": props["design_daily_demand_l"],
                    "fed_by": props["fed_by"],
                    "center": props["center"],
                    # Baseline demand in L/min = daily demand / 1440
                    "base_lpm": round(props["design_daily_demand_l"] / 1440.0, 2),
                    "current_lpm": round(props["design_daily_demand_l"] / 1440.0, 2),
                    "meter_reading_lpm": round(props["design_daily_demand_l"] / 1440.0, 2),
                    "meter_quality": "good",
                    "pressure_bar": 2.45
                }
            elif geom["type"] == "Point":
                if f_type == "tank":
                    self.tanks[props["id"]] = {
                        "id": props["id"],
                        "name": props["name"],
                        "capacity_kl": props["capacity_kl"],
                        "max_head_m": 5.0, # 5 meters tall
                        "current_kl": props["capacity_kl"] * 0.82,
                        "current_level_m": 5.0 * 0.82,
                        "inflow_lpm": 0.0,
                        "outflow_lpm": 0.0,
                        "pump_active": False,
                        "coordinates": geom["coordinates"]
                    }
                elif f_type == "sump":
                    self.sump = {
                        "id": props["id"],
                        "name": props["name"],
                        "capacity_kl": props["capacity_kl"],
                        "max_head_m": 6.0,
                        "current_kl": props["capacity_kl"] * 0.78,
                        "current_level_m": 6.0 * 0.78,
                        "raw_inflow_lpm": 450.0,
                        "pump_outflow_lpm": 380.0,
                        "coordinates": geom["coordinates"]
                    }
                elif f_type == "borewell":
                    self.borewells[props["id"]] = {
                        "id": props["id"],
                        "name": props["name"],
                        "max_yield_lpm": props["max_yield_lpm"],
                        "current_yield_lpm": props["max_yield_lpm"] * 0.95,
                        "status": "running",
                        "depth_m": 180.0 if "BW-01" in props["id"] else 210.0,
                        "coordinates": geom["coordinates"]
                    }
                elif f_type == "municipal_inlet":
                    self.muni_inlet = {
                        "id": props["id"],
                        "name": props["name"],
                        "flow_lpm": 104.0, # ~150 kL / day
                        "coordinates": geom["coordinates"]
                    }
                elif f_type == "STP":
                    self.stp = {
                        "id": props["id"],
                        "name": props["name"],
                        "capacity_kld": props.get("capacity_kld", props.get("capacity_kl") or 150.0),
                        "current_treated_kld": 112.0,
                        "recycled_lpm": 78.0,
                        "coordinates": geom["coordinates"]
                    }
            elif geom["type"] == "LineString":
                self.pipes[props["id"]] = {
                    "id": props["id"],
                    "from_node": props["from_node"],
                    "to_node": props["to_node"],
                    "diameter_mm": props["diameter_mm"],
                    "length_m": props["length_m"],
                    "flow_lpm": 0.0,
                    "pressure_bar": 2.5,
                    "true_leak_lpm": 0.0,
                    "has_fault": False,
                    "coordinates": geom["coordinates"]
                }

    def _init_faults_and_ground_truth(self):
        """Active ground truth faults registered in the physical engine."""
        self.active_faults: Dict[str, Dict[str, Any]] = {}
        self.complaints_queue: List[Dict[str, Any]] = []

    def _init_state(self):
        self.academic_calendar = CALENDAR_SEMESTER
        self.weather_temp_c = 28.5
        self.weather_rainfall_mm = 0.0
        self.weather_forecast_72h = self._generate_72h_forecast()

    def _generate_72h_forecast(self) -> List[Dict[str, Any]]:
        forecast = []
        now = self.get_sim_time()
        for h in range(72):
            future_time = now + timedelta(hours=h)
            hour_of_day = future_time.hour
            temp = round(24.0 + 8.5 * math.sin((hour_of_day - 8.0) / 12.0 * math.pi) + self.rng.uniform(-1.0, 1.0), 1)
            # Occasional rain probability
            prob = 10 if h < 36 else 35
            forecast.append({
                "hour_offset": h,
                "timestamp": future_time.isoformat(),
                "temp_c": temp,
                "rain_prob_pct": prob,
                "rainfall_predicted_mm": 2.5 if prob > 30 else 0.0
            })
        return forecast

    def get_sim_time(self) -> datetime:
        return self.base_time + timedelta(minutes=self.current_tick * 5)

    def _get_diurnal_factor(self, hour: float, b_type: str, is_weekend: bool) -> float:
        """Computes diurnal multiplier for block flow."""
        if b_type == "residential": # Hostels
            if not is_weekend:
                # Morning peak 5:00 to 8:30
                if 5.0 <= hour <= 8.5:
                    curve = math.sin((hour - 5.0) / 3.5 * math.pi)
                    return 1.4 + 1.2 * curve # 2.6x peak
                elif 18.0 <= hour <= 21.5:
                    curve = math.sin((hour - 18.0) / 3.5 * math.pi)
                    return 1.2 + 0.9 * curve
                elif 0.5 <= hour <= 4.5:
                    return 0.12 # Minimum night flow
                elif 9.5 <= hour <= 17.0:
                    return 0.28 # Day classes
                else:
                    return 0.60
            else: # Weekend: wake up later
                if 7.0 <= hour <= 10.5:
                    curve = math.sin((hour - 7.0) / 3.5 * math.pi)
                    return 1.3 + 1.1 * curve
                elif 18.5 <= hour <= 22.5:
                    return 1.6
                elif 1.0 <= hour <= 5.5:
                    return 0.14
                else:
                    return 0.70

        elif b_type == "mess": # Central dining
            if 5.5 <= hour <= 8.5: # Breakfast
                return 2.2
            elif 11.5 <= hour <= 14.5: # Lunch
                return 2.8
            elif 17.5 <= hour <= 21.0: # Dinner
                return 2.4
            elif 0.0 <= hour <= 4.5:
                return 0.05
            else:
                return 0.35

        elif b_type in ["academic", "library", "labs"]:
            if not is_weekend:
                if 8.5 <= hour <= 17.5:
                    curve = math.sin((hour - 8.5) / 9.0 * math.pi)
                    return 0.9 + 0.7 * curve # 1.6x peak
                elif 0.0 <= hour <= 6.0:
                    return 0.03
                else:
                    return 0.25
            else:
                return 0.15 # Weekend mostly empty

        elif b_type == "health":
            return 1.2 if 8.0 <= hour <= 20.0 else 0.8

        elif b_type == "sports ground":
            if 5.5 <= hour <= 8.5 or 16.5 <= hour <= 20.0:
                return 2.2
            elif 0.0 <= hour <= 5.0:
                return 0.04
            else:
                return 0.30

        return 0.75

    def inject_fault(self, fault_type: str, entity_id: str, true_loss_rate_lpm: float = 40.0, details: str = ""):
        """
        Inject a true physical or sensor fault into the digital twin (Ground Truth).
        Stores in SQLite ground_truth table.
        """
        fault_id = f"FAULT-{self.current_tick}-{self.rng.randint(100, 999)}"
        f_record = {
            "fault_id": fault_id,
            "fault_type": fault_type,
            "entity_id": entity_id,
            "start_tick": self.current_tick,
            "true_loss_rate_lpm": true_loss_rate_lpm,
            "details": details or f"Injected {fault_type} on {entity_id}",
            "is_active": True
        }
        self.active_faults[fault_id] = f_record

        # Apply immediately to physical model
        if fault_type in ["small_slow_leak", "burst_main"] and entity_id in self.pipes:
            self.pipes[entity_id]["true_leak_lpm"] = true_loss_rate_lpm
            self.pipes[entity_id]["has_fault"] = True
        elif fault_type == "running_toilet_overflow" and entity_id in self.blocks:
            pass # dynamic demand adder handles this in tick
        elif fault_type in ["meter_fault", "sensor_dropout"] and entity_id in self.blocks:
            pass

        # Persist to SQLite
        with Session(engine) as session:
            gt = GroundTruth(
                fault_id=fault_id,
                fault_type=fault_type,
                entity_id=entity_id,
                start_tick=self.current_tick,
                true_loss_rate_lpm=true_loss_rate_lpm,
                details=f_record["details"],
                is_active=True
            )
            session.add(gt)
            ev = SystemEvent(
                tick=self.current_tick,
                event_type="FAULT_INJECTED",
                entity_id=entity_id,
                severity="critical" if "burst" in fault_type else "watch",
                details=f"Ground truth fault {fault_type} registered at tick {self.current_tick}"
            )
            session.add(ev)
            session.commit()

        # Schedule delayed complaint (e.g. 12 to 24 ticks later = 1-2 hours)
        lag_ticks = self.rng.randint(12, 28)
        complaint_text = self._get_complaint_text_for_fault(fault_type, entity_id)
        self.complaints_queue.append({
            "trigger_tick": self.current_tick + lag_ticks,
            "entity_id": entity_id,
            "category": "plumbing" if "leak" in fault_type or "burst" in fault_type else "pressure",
            "text": complaint_text
        })

        return {"status": "ok", "fault_id": fault_id, "record": f_record}

    def _get_complaint_text_for_fault(self, fault_type: str, entity_id: str) -> str:
        if fault_type == "burst_main":
            return f"Water gushing from ground near {entity_id}; low pressure across entire wing."
        elif fault_type == "running_toilet_overflow":
            return f"Second floor washroom cistern continuously running and overflowing onto corridor."
        elif fault_type == "small_slow_leak":
            return f"Damp soil and faint hissing noise observed near pipe junction {entity_id}."
        elif fault_type == "tank_float_valve_failure":
            return f"Overhead tank {entity_id} overflowing from top vent down external staircase."
        elif fault_type == "meter_fault":
            return f"Digital telemetry display blinking zero at block {entity_id} panel."
        return f"Issue observed at {entity_id}."

    def tick(self, steps: int = 1):
        """Advance the simulation state by steps ticks (each tick = 5 minutes)."""
        if self.is_paused:
            return self.get_state()

        step_multiplier = steps * self.speed
        readings_batch = []

        for _ in range(step_multiplier):
            self.current_tick += 1
            sim_time = self.get_sim_time()
            hour = sim_time.hour + (sim_time.minute / 60.0)
            is_weekend = sim_time.weekday() >= 5

            # 1. Weather Update
            self.weather_temp_c = round(24.0 + 8.5 * math.sin((hour - 8.0) / 12.0 * math.pi) + self.rng.uniform(-0.4, 0.4), 1)
            # Occasional rainfall
            if self.rng.random() < 0.015:
                self.weather_rainfall_mm = round(self.rng.uniform(2.0, 18.0), 1)
            else:
                self.weather_rainfall_mm = 0.0

            # 2. Borewell yield with slow seasonal decline
            total_borewell_lpm = 0.0
            day_num = self.current_tick / 288.0
            seasonal_factor = max(0.70, 1.0 - (day_num / 365.0) * 0.15)
            for bw in self.borewells.values():
                if bw["status"] == "running":
                    bw["current_yield_lpm"] = round(bw["max_yield_lpm"] * seasonal_factor + self.rng.uniform(-2.0, 2.0), 1)
                    total_borewell_lpm += bw["current_yield_lpm"]

            # 3. Sump Inflow & Level
            muni_lpm = self.muni_inlet["flow_lpm"] if self.muni_inlet else 0.0
            rain_harvest_lpm = self.weather_rainfall_mm * 18.0
            total_raw_inflow = total_borewell_lpm + muni_lpm + rain_harvest_lpm
            self.sump["raw_inflow_lpm"] = round(total_raw_inflow, 1)

            # 4. Block Demands & Fault Application
            tank_demands = {t_id: 0.0 for t_id in self.tanks}

            for blk_id, blk in self.blocks.items():
                mult = self._get_diurnal_factor(hour, blk["type"], is_weekend)
                noise = self.rng.uniform(0.95, 1.05)
                cal_mult = 1.05 if self.academic_calendar == CALENDAR_EXAM else (0.25 if self.academic_calendar == CALENDAR_VACATION else 1.0)

                true_demand = blk["base_lpm"] * mult * cal_mult * noise

                # Apply active toilet overflow fault
                for f in self.active_faults.values():
                    if f["is_active"] and f["entity_id"] == blk_id and f["fault_type"] == "running_toilet_overflow":
                        true_demand += f["true_loss_rate_lpm"]

                blk["current_lpm"] = round(true_demand, 1)
                tank_demands[blk["fed_by"]] += true_demand

                # Determine Meter Reading (Check for meter fault or dropout)
                has_meter_fault = False
                has_dropout = False
                for f in self.active_faults.values():
                    if f["is_active"] and f["entity_id"] == blk_id:
                        if f["fault_type"] == "meter_fault":
                            has_meter_fault = True
                        elif f["fault_type"] == "sensor_dropout":
                            has_dropout = True

                if has_dropout:
                    blk["meter_reading_lpm"] = 0.0
                    blk["meter_quality"] = "dropout"
                elif has_meter_fault:
                    blk["meter_reading_lpm"] = 0.0 # flatline zero
                    blk["meter_quality"] = "faulty"
                else:
                    # Sensor reading with small Gaussian noise
                    blk["meter_reading_lpm"] = round(max(0.0, true_demand + self.rng.gauss(0, 0.4)), 1)
                    blk["meter_quality"] = "good"

                # Hydraulic Pressure at Block: Static tank head minus pipe friction drop
                tank = self.tanks.get(blk["fed_by"])
                base_head = 2.0 + (tank["current_level_m"] / tank["max_head_m"]) * 0.8
                friction_drop = (true_demand / 100.0) ** 1.85 * 0.14
                pressure = base_head - friction_drop

                # If pipe supplying this block has leak, pressure drops sharply!
                for p in self.pipes.values():
                    if p["to_node"] == blk_id and p["has_fault"]:
                        pressure -= (p["true_leak_lpm"] / 50.0) * 0.70

                blk["pressure_bar"] = round(max(0.40, pressure + self.rng.uniform(-0.02, 0.02)), 2)

            # 5. Tank Hydraulics (Mass Balance)
            total_sump_pump_outflow = 0.0
            for t_id, tank in self.tanks.items():
                outflow_lpm = tank_demands[t_id]

                # Check if pipe from tank has leak
                for p in self.pipes.values():
                    if p["from_node"] == t_id and p["has_fault"]:
                        outflow_lpm += p["true_leak_lpm"]

                tank["outflow_lpm"] = round(outflow_lpm, 1)

                # Float valve failure fault
                has_float_failure = any(
                    f["is_active"] and f["entity_id"] == t_id and f["fault_type"] == "tank_float_valve_failure"
                    for f in self.active_faults.values()
                )

                # Automated pump logic
                pct_full = (tank["current_kl"] / tank["capacity_kl"]) * 100.0
                if pct_full < 40.0:
                    tank["pump_active"] = True
                    tank["inflow_lpm"] = 240.0 if t_id == "OHT-HOSTEL" else 180.0
                elif pct_full > 92.0 and not has_float_failure:
                    tank["pump_active"] = False
                    tank["inflow_lpm"] = 0.0

                if has_float_failure:
                    tank["inflow_lpm"] = 220.0 # continues pumping and overflows!

                total_sump_pump_outflow += tank["inflow_lpm"]

                # Delta V (kL) in 5 minutes = (Inflow - Outflow) * 5 / 1000
                delta_kl = ((tank["inflow_lpm"] - tank["outflow_lpm"]) * 5.0) / 1000.0
                tank["current_kl"] = max(2.0, min(tank["capacity_kl"], tank["current_kl"] + delta_kl))
                tank["current_level_m"] = round((tank["current_kl"] / tank["capacity_kl"]) * tank["max_head_m"], 2)

            # 6. Sump Hydraulics
            self.sump["pump_outflow_lpm"] = round(total_sump_pump_outflow, 1)
            sump_delta_kl = ((self.sump["raw_inflow_lpm"] - self.sump["pump_outflow_lpm"]) * 5.0) / 1000.0
            self.sump["current_kl"] = max(20.0, min(self.sump["capacity_kl"], self.sump["current_kl"] + sump_delta_kl))
            self.sump["current_level_m"] = round((self.sump["current_kl"] / self.sump["capacity_kl"]) * self.sump["max_head_m"], 2)

            # 7. Check Complaints Queue
            for c in list(self.complaints_queue):
                if self.current_tick >= c["trigger_tick"]:
                    with Session(engine) as session:
                        ev = SystemEvent(
                            tick=self.current_tick,
                            event_type="COMPLAINT_FILED",
                            entity_id=c["entity_id"],
                            severity="watch",
                            details=f"Student/Staff complaint received for {c['entity_id']}: {c['text']}"
                        )
                        session.add(ev)
                        session.commit()
                    self.complaints_queue.remove(c)

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """Returns the full latest tick state snapshot."""
        sim_time = self.get_sim_time()
        hour = sim_time.hour + (sim_time.minute / 60.0)

        total_demand = sum(b["current_lpm"] for b in self.blocks.values())
        total_storage_kl = self.sump["current_kl"] + sum(t["current_kl"] for t in self.tanks.values())
        avg_burn_kl_hr = (total_demand * 60.0) / 1000.0
        reserve_hours = round(total_storage_kl / max(1.0, avg_burn_kl_hr), 1)

        return {
            "tick": self.current_tick,
            "sim_time": sim_time.isoformat(),
            "day_name": sim_time.strftime("%A"),
            "hour_of_day": round(hour, 2),
            "academic_calendar": self.academic_calendar,
            "speed": self.speed,
            "is_paused": self.is_paused,
            "seed": self.seed,
            "weather": {
                "temp_c": self.weather_temp_c,
                "rainfall_mm": self.weather_rainfall_mm,
                "forecast_72h_sample": self.weather_forecast_72h[:12]
            },
            "sump": {
                "id": self.sump["id"],
                "name": self.sump["name"],
                "capacity_kl": self.sump["capacity_kl"],
                "current_kl": round(self.sump["current_kl"], 1),
                "level_m": self.sump["current_level_m"],
                "pct_full": round((self.sump["current_kl"] / self.sump["capacity_kl"]) * 100.0, 1),
                "raw_inflow_lpm": self.sump["raw_inflow_lpm"],
                "pump_outflow_lpm": self.sump["pump_outflow_lpm"]
            },
            "tanks": [
                {
                    "id": t["id"],
                    "name": t["name"],
                    "capacity_kl": t["capacity_kl"],
                    "current_kl": round(t["current_kl"], 1),
                    "level_m": t["current_level_m"],
                    "pct_full": round((t["current_kl"] / t["capacity_kl"]) * 100.0, 1),
                    "inflow_lpm": t["inflow_lpm"],
                    "outflow_lpm": t["outflow_lpm"],
                    "pump_active": t["pump_active"]
                }
                for t in self.tanks.values()
            ],
            "borewells": [
                {
                    "id": b["id"],
                    "name": b["name"],
                    "max_yield_lpm": b["max_yield_lpm"],
                    "current_yield_lpm": b["current_yield_lpm"],
                    "status": b["status"]
                }
                for b in self.borewells.values()
            ],
            "blocks": [
                {
                    "id": b["id"],
                    "name": b["name"],
                    "code": b["code"],
                    "type": b["type"],
                    "population": b["population"],
                    "vulnerable": b["vulnerable"],
                    "current_lpm": b["current_lpm"],
                    "meter_reading_lpm": b["meter_reading_lpm"],
                    "meter_quality": b["meter_quality"],
                    "pressure_bar": b["pressure_bar"],
                    "fed_by": b["fed_by"]
                }
                for b in self.blocks.values()
            ],
            "pipes": [
                {
                    "id": p["id"],
                    "from_node": p["from_node"],
                    "to_node": p["to_node"],
                    "diameter_mm": p["diameter_mm"],
                    "flow_lpm": p["flow_lpm"],
                    "pressure_bar": p["pressure_bar"],
                    "true_leak_lpm": p["true_leak_lpm"],
                    "has_fault": p["has_fault"]
                }
                for p in self.pipes.values()
            ],
            "kpis": {
                "total_demand_lpm": round(total_demand, 1),
                "total_storage_kl": round(total_storage_kl, 1),
                "reserve_hours": reserve_hours,
                "active_faults_count": len([f for f in self.active_faults.values() if f["is_active"]])
            }
        }

    def reset(self, seed: Optional[int] = None):
        """Resets the digital twin to tick 0 with seed."""
        if seed is not None:
            self.seed = seed
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        self.current_tick = 0
        self._parse_topology()
        self._init_faults_and_ground_truth()
        self._init_state()
        return self.get_state()

# Global Phase 3 simulator singleton
sim_engine = CampusSimulatorPhase3(seed=42)
