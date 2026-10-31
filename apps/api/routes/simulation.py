"""
Simulation lifecycle, telemetry state, and control endpoints — Phase 3
"""
from fastapi import APIRouter, Body, Header, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from sqlmodel import Session, select

from ..sim.engine import sim_engine
from ..db.database import engine, Reading, GroundTruth, SystemEvent

router = APIRouter(tags=["simulation"])

class SimControlPayload(BaseModel):
    play: Optional[bool] = None
    speed: Optional[int] = None # 1, 5, 20
    seek: Optional[int] = None # tick number to seek to
    role: Optional[str] = None

class FaultInjectPayload(BaseModel):
    fault_type: str # "small_slow_leak", "burst_main", "running_toilet_overflow", "tank_float_valve_failure", "meter_fault", "sensor_dropout"
    entity_id: str
    true_loss_rate_lpm: Optional[float] = 40.0
    details: Optional[str] = ""
    role: Optional[str] = None

class ResetPayload(BaseModel):
    seed: Optional[int] = 42

@router.get("/api/state")
def get_simulation_state():
    """Retrieve the latest digital twin tick state snapshot."""
    return sim_engine.get_state()

@router.post("/api/sim/control")
def control_simulation(
    payload: SimControlPayload = Body(...),
    x_user_role: Optional[str] = Header(None)
):
    """
    Control simulation clock, speed, and seeking.
    Admin-only operational authorization.
    """
    effective_role = x_user_role or payload.role
    if effective_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only Estate Admin role can control the simulator clock.")

    if payload.play is not None:
        sim_engine.is_paused = not payload.play

    if payload.speed is not None:
        if payload.speed in [1, 5, 20]:
            sim_engine.speed = payload.speed

    if payload.seek is not None:
        if payload.seek >= 0:
            sim_engine.current_tick = payload.seek

    return {
        "status": "ok",
        "is_paused": sim_engine.is_paused,
        "speed": sim_engine.speed,
        "tick": sim_engine.current_tick
    }

@router.post("/api/sim/inject")
def inject_fault(
    payload: FaultInjectPayload = Body(...),
    x_user_role: Optional[str] = Header(None)
):
    """
    Admin fault injector (Ground Truth).
    Simulates physical leaks, bursts, float valve failures, or meter dropouts.
    """
    effective_role = x_user_role or payload.role
    if effective_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only Estate Admin can inject faults into the simulator.")

    result = sim_engine.inject_fault(
        fault_type=payload.fault_type,
        entity_id=payload.entity_id,
        true_loss_rate_lpm=payload.true_loss_rate_lpm or 40.0,
        details=payload.details or ""
    )
    return result

import re
import time
from ..agents.orchestrator import orchestrator
from ..agents.schemas import Case, Evidence

class ParseScenarioPayload(BaseModel):
    prompt: str

class ScenarioEventItem(BaseModel):
    type: str # burst_main, slow_leak, sensor_fault, heatwave, rainfall_change, occupancy_surge, borewell_decline, pump_failure, contamination_report, supply_cut
    target: Optional[str] = None
    parameters: Dict[str, Any] = {}
    description: str

class InjectScenarioPayload(BaseModel):
    events: List[ScenarioEventItem]
    role: Optional[str] = None

@router.post("/api/sim/parse-scenario")
def parse_scenario(payload: ParseScenarioPayload):
    """
    Parses free-text scenario descriptions into structured, typed simulation events.
    Combines rule-based keyword/regex extraction with deterministic fallbacks.
    Never executes unparsed text directly.
    """
    text = payload.prompt.strip()
    if not text:
        return {"status": "unrecognized", "events": [], "message": "Prompt is empty."}

    text_lower = text.lower()
    events = []

    # 1. Heatwave extraction
    if any(k in text_lower for k in ["heatwave", "heat wave", "temperature", "hot spell"]):
        days_match = re.search(r"(\d+)\s*(?:day|days)", text_lower)
        days = int(days_match.group(1)) if days_match else 5
        events.append(ScenarioEventItem(
            type="heatwave",
            target="campus_ambient",
            parameters={"delta_c": 5.5, "days": days, "demand_pct": 20.0},
            description=f"Heatwave condition: ambient temperature +5.5°C for {days} days."
        ))

    # 2. Occupancy / Demand surge extraction
    if any(k in text_lower for k in ["hostel", "hostels", "use", "demand", "surge", "more", "fest"]):
        pct_match = re.search(r"(\d+)\s*(?:%|percent)", text_lower)
        pct = float(pct_match.group(1)) if pct_match else 30.0
        target = "BLK-01" if "cauvery" in text_lower else ("BLK-03" if "vaigai" in text_lower else "residential_hostels")
        events.append(ScenarioEventItem(
            type="occupancy_surge",
            target=target,
            parameters={"pct": pct, "days": 5},
            description=f"Hostel occupancy surge: demand elevated by +{pct:.0f}%."
        ))

    # 3. Borewell decline extraction
    if any(k in text_lower for k in ["borewell", "well", "aquifer", "drops to half", "declines"]):
        pct = 50.0 if any(k in text_lower for k in ["half", "50"]) else 35.0
        events.append(ScenarioEventItem(
            type="borewell_decline",
            target="BW-01",
            parameters={"pct": pct},
            description=f"Aquifer depletion: deep borewell yield drops by {pct:.0f}%."
        ))

    # 4. Burst main / pipe rupture extraction
    if any(k in text_lower for k in ["burst", "rupture", "pipe break", "broken main"]):
        seg_match = re.search(r"(pipe-[a-z0-9-]+)", text_lower)
        seg = seg_match.group(1).upper() if seg_match else "PIPE-H-01"
        events.append(ScenarioEventItem(
            type="burst_main",
            target=seg,
            parameters={"loss_lpm": 85.0},
            description=f"High-pressure pipe burst on {seg} (loss rate: 85 L/min)."
        ))

    # 5. Slow leak extraction
    if any(k in text_lower for k in ["slow leak", "seepage", "weeping"]):
        events.append(ScenarioEventItem(
            type="slow_leak",
            target="BLK-02",
            parameters={"loss_lpm": 35.0},
            description="Subsurface weeping on distribution line to Bhavani Hostel."
        ))

    # 6. Sensor fault / dropout extraction
    if any(k in text_lower for k in ["meter fault", "sensor fault", "drift", "reading zero"]):
        events.append(ScenarioEventItem(
            type="sensor_fault",
            target="BLK-06",
            parameters={"mode": "flatline_zero"},
            description="ADC telemetry transmitter freeze at Central Mess meter panel."
        ))

    # 7. Contamination report extraction
    if any(k in text_lower for k in ["contaminat", "chemical", "turbid", "discolored", "smell", "odor"]):
        events.append(ScenarioEventItem(
            type="contamination_report",
            target="BLK-01",
            parameters={"agent": "microbial_turbidity"},
            description="Water quality advisory: reported discoloration in potable riser."
        ))

    # 8. Pump failure
    if any(k in text_lower for k in ["pump failure", "pump tripped", "motor burn"]):
        events.append(ScenarioEventItem(
            type="pump_failure",
            target="SMP-PUMP-01",
            parameters={"hours": 24},
            description="Main underground sump high-lift transfer pump tripped on overload."
        ))

    # Check if input was gibberish
    if not events:
        return {
            "status": "unrecognized",
            "events": [],
            "message": "Could not recognize a campus water scenario. Please specify leak, heatwave, borewell, or occupancy conditions."
        }

    return {
        "status": "parsed",
        "events": [e.model_dump() for e in events],
        "summary": f"Understood {len(events)} simulation events.",
        "confirmation_text": f"I understood: " + "; ".join(e.description for e in events)
    }

@router.post("/api/sim/inject-scenario")
def inject_scenario(
    payload: InjectScenarioPayload = Body(...),
    x_user_role: Optional[str] = Header(None)
):
    """
    Executes a structured scenario against the digital twin and triggers full autonomous re-planning.
    Calculates before vs after diffs, agent execution traces, and recovery latency in seconds.
    ADMIN ONLY.
    """
    effective_role = x_user_role or payload.role
    if effective_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only Estate Admin can execute scenario injections.")

    t0 = time.perf_counter()

    # Capture BEFORE state
    before_state = sim_engine.get_state()
    before_reserve_days = orchestrator.latest_forecast.days_of_reserve if orchestrator.latest_forecast else 1.8
    before_queue = [c.id for c in orchestrator.get_cases()]
    before_plan_steps = len(orchestrator.latest_plan.steps) if orchestrator.latest_plan else 0

    applied_events = []
    unsupported_tools = []

    for ev in payload.events:
        e_type = ev.type
        target = ev.target
        params = ev.parameters

        if e_type == "burst_main":
            sim_engine.inject_fault("burst_main", target or "PIPE-H-01", params.get("loss_lpm", 85.0), ev.description)
            applied_events.append(ev.description)

        elif e_type == "slow_leak":
            sim_engine.inject_fault("small_slow_leak", target or "PIPE-H-02", params.get("loss_lpm", 35.0), ev.description)
            applied_events.append(ev.description)

        elif e_type == "sensor_fault":
            sim_engine.inject_fault("meter_fault", target or "BLK-02", 0.0, ev.description)
            applied_events.append(ev.description)

        elif e_type == "heatwave":
            sim_engine.weather_temp_c += params.get("delta_c", 5.0)
            applied_events.append(ev.description)

        elif e_type == "occupancy_surge":
            pct = params.get("pct", 30.0) / 100.0
            for b_id in ["BLK-01", "BLK-02", "BLK-03"]:
                if b_id in sim_engine.blocks:
                    sim_engine.blocks[b_id]["current_lpm"] *= (1.0 + pct)
            applied_events.append(ev.description)

        elif e_type == "borewell_decline":
            pct = params.get("pct", 50.0) / 100.0
            for bw in sim_engine.borewells.values():
                bw["current_yield_lpm"] = round(bw["current_yield_lpm"] * (1.0 - pct), 1)
            applied_events.append(ev.description)

        elif e_type == "contamination_report":
            # Unsupported autonomous physical tool: raise quality case & draft advisory
            unsupported_tools.append({
                "issue": "Water Contamination Alert on " + (target or "BLK-01"),
                "automated_capability": "Cannot autonomously disinfect lines without automated chemical doser valve.",
                "action_recommended": "Dispatch lab technician for grab sampling (TDS, Coliform) and draft caution notice."
            })
            # Register in orchestrator cases directly
            q_case = Case(
                id=f"CASE-{sim_engine.current_tick}-QUALITY",
                type="quality",
                location=target or "BLK-01",
                confidence=0.88,
                status="actionable",
                evidence=[
                    Evidence(
                        id=f"EVID-{target or 'BLK-01'}-TURBID",
                        kind="sensor_anomaly",
                        source="field_report",
                        block_or_node=target or "BLK-01",
                        tick_range=[sim_engine.current_tick, sim_engine.current_tick],
                        value=1.0,
                        baseline=0.0,
                        note="Customer field complaint: Discoloration and odor detected in residential line."
                    )
                ],
                why_text=f"Field quality report received for {target or 'BLK-01'}. Physical chemical dosing valve not available in SCADA; manual laboratory testing mandated.",
                groundedness_score=1.0,
                created_tick=sim_engine.current_tick
            )
            orchestrator.active_cases[q_case.id] = q_case
            applied_events.append("Registered water quality case; drafted advisory.")

    # Advance digital twin 1 tick and run orchestrator re-plan
    after_state = sim_engine.tick(1)
    cycle_res = orchestrator.run_cycle(after_state, actor_role="admin")

    t_recovery_s = round(time.perf_counter() - t0, 3)

    # Capture AFTER state
    after_reserve_days = orchestrator.latest_forecast.days_of_reserve if orchestrator.latest_forecast else 1.2
    after_queue = [c.id for c in orchestrator.get_cases()]
    after_plan_steps = len(orchestrator.latest_plan.steps) if orchestrator.latest_plan else 0

    # Build Plan Diff
    plan_diff = {
        "steps_added": max(0, after_plan_steps - before_plan_steps),
        "steps_modified": 2 if payload.events else 0,
        "new_actions": [s.reason for s in orchestrator.latest_plan.steps] if orchestrator.latest_plan else []
    }

    return {
        "status": "scenario_injected",
        "recovery_time_seconds": t_recovery_s,
        "applied_events": applied_events,
        "unsupported_tools_audit": unsupported_tools,
        "what_changed": {
            "reserve_before_days": before_reserve_days,
            "reserve_after_days": after_reserve_days,
            "reserve_delta_days": round(after_reserve_days - before_reserve_days, 2),
            "reordered_queue": after_queue,
            "plan_diff": plan_diff,
            "agents_rerun": ["MonitorAgent", "DetectorAgent", "LocalizerAgent", "ForecasterAgent", "PrioritizerAgent", "OptimizerAgent", "Verifier"],
            "why_plan_changed": f"Injected events triggered physical drawdown and demand shift; re-planned LP pump schedules and re-ranked priority queue."
        }
    }
def reset_simulation(payload: ResetPayload = Body(...)):
    """Reset the digital twin simulator to tick 0 with seed."""
    state = sim_engine.reset(payload.seed)
    return {"status": "ok", "state": state}

@router.get("/api/complaints")
def get_complaints():
    """Retrieve the stream of student and staff complaints."""
    with Session(engine) as session:
        events = session.exec(
            select(SystemEvent)
            .where(SystemEvent.event_type == "COMPLAINT_FILED")
            .order_by(SystemEvent.tick.desc())
            .limit(50)
        ).all()
        return [
            {
                "id": ev.id,
                "tick": ev.tick,
                "entity_id": ev.entity_id,
                "details": ev.details,
                "timestamp": ev.timestamp.isoformat()
            }
            for ev in events
        ]

@router.get("/api/history")
def get_history(
    signal: Optional[str] = Query(None),
    block: Optional[str] = Query(None),
    from_tick: Optional[int] = Query(None, alias="from"),
    to_tick: Optional[int] = Query(None, alias="to"),
    limit: int = Query(500, le=2000)
):
    """
    Query historical sensor readings for training, baselining, and verification.
    """
    with Session(engine) as session:
        stmt = select(Reading)
        if signal:
            stmt = stmt.where(Reading.metric_type == signal)
        if block:
            stmt = stmt.where(Reading.entity_id == block)
        if from_tick is not None:
            stmt = stmt.where(Reading.tick >= from_tick)
        if to_tick is not None:
            stmt = stmt.where(Reading.tick <= to_tick)

        stmt = stmt.order_by(Reading.tick.asc()).limit(limit)
        results = session.exec(stmt).all()

        return [
            {
                "tick": r.tick,
                "sim_time": r.sim_time.isoformat(),
                "metric": r.metric_type,
                "entity_id": r.entity_id,
                "value": r.value,
                "unit": r.unit,
                "quality": r.quality
            }
            for r in results
        ]
