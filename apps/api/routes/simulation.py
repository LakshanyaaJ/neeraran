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

@router.post("/api/sim/reset")
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
