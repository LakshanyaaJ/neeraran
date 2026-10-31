"""
Simulation lifecycle and real-time state endpoints.
"""
from fastapi import APIRouter, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..sim.engine import simulator_instance
from ..sim.state import SimulationState

router = APIRouter(prefix="/api/sim", tags=["simulation"])

class SpeedPayload(BaseModel):
    speed: int

class PausePayload(BaseModel):
    paused: bool

class LeakPayload(BaseModel):
    pipe_id: str
    leak_rate_lpm: float = 45.0

class TickPayload(BaseModel):
    minutes: float = 1.0

class ResetPayload(BaseModel):
    seed: Optional[int] = 42

@router.get("/state", response_model=SimulationState)
def get_current_state():
    """Retrieve current digital twin simulated telemetry and status."""
    return simulator_instance.get_state()

@router.post("/tick", response_model=SimulationState)
def step_simulation(payload: TickPayload = Body(...)):
    """Advance simulation forward by a given virtual time step."""
    return simulator_instance.tick(payload.minutes)

@router.post("/speed")
def update_speed(payload: SpeedPayload = Body(...)):
    """Set simulation speed multiplier (1x, 5x, 20x)."""
    return simulator_instance.set_speed(payload.speed)

@router.post("/pause")
def toggle_pause(payload: PausePayload = Body(...)):
    """Pause or resume the simulation clock."""
    return simulator_instance.set_paused(payload.paused)

@router.post("/reset")
def reset_simulation(payload: ResetPayload = Body(...)):
    """Reset the digital twin simulator to seeded initial state."""
    return simulator_instance.reset(payload.seed)

@router.post("/leak/inject")
def inject_leak(payload: LeakPayload = Body(...)):
    """Inject a physical leak scenario onto a pipe segment."""
    return simulator_instance.inject_leak(payload.pipe_id, payload.leak_rate_lpm)

@router.post("/leak/clear")
def clear_leak(payload: LeakPayload = Body(...)):
    """Clear an existing leak on a pipe segment."""
    return simulator_instance.clear_leak(payload.pipe_id)

@router.get("/snapshot")
def get_snapshot() -> Dict[str, Any]:
    """Export complete current digital twin state as snapshot dictionary."""
    state = simulator_instance.get_state()
    return state.model_dump()
