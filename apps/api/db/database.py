"""
SQLModel database schema for NEERARAN Phase 3.
Tables:
- readings (rolling window of raw sensor telemetry)
- ground_truth (true faults, leak locations, true loss rates - hidden from agents)
- events (system event log)
- approvals (action items waiting for admin approval)
- audit_log (immutable actor actions and verifications)
- tickets (CMMS work order tickets)
"""
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Session, create_engine, select

DATABASE_URL = "sqlite:///./apps/api/neeraran.db"
engine = create_engine(DATABASE_URL, echo=False)

def get_utc_now():
    return datetime.now(timezone.utc)

class Reading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tick: int = Field(index=True)
    sim_time: datetime
    metric_type: str = Field(index=True) # "block_flow", "pipe_pressure", "tank_level", "weather", "borewell_yield"
    entity_id: str = Field(index=True) # e.g. "BLK-01", "PIPE-H-03", "OHT-HOSTEL"
    value: float
    unit: str # "L/min", "bar", "m", "mm/h"
    quality: str = "good" # "good", "faulty", "dropout"

class GroundTruth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fault_id: str = Field(index=True) # "FAULT-01"
    fault_type: str # "small_slow_leak", "burst_main", "running_toilet_overflow", "tank_float_valve_failure", "meter_fault", "sensor_dropout"
    entity_id: str = Field(index=True) # location
    start_tick: int = Field(index=True)
    end_tick: Optional[int] = None
    true_loss_rate_lpm: float = 0.0 # 0 for meter fault / dropout
    details: str
    is_active: bool = True

class SystemEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tick: int = Field(index=True)
    event_type: str # "FAULT_INJECTED", "LEAK_DETECTED", "COMPLAINT_FILED", "PUMP_TOGGLED"
    entity_id: str
    severity: str = "info" # "info", "watch", "critical"
    details: str
    evidence_ids: Optional[str] = None
    timestamp: datetime = Field(default_factory=get_utc_now)

class ApprovalItem(SQLModel, table=True):
    id: str = Field(primary_key=True) # e.g. "REQ-8021"
    title: str
    description: str
    category: str # "pressure_modulation", "zone_rationing", "pump_dispatch"
    is_vulnerable: bool = False
    equity_impact_check: str
    proposed_actions: str # JSON
    rollback_step: str # JSON
    evidence_ids: str
    created_at: datetime = Field(default_factory=get_utc_now)
    status: str = "pending" # "pending", "approved", "rejected"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=get_utc_now)
    actor: str
    role: str
    action_type: str
    target_resource: str
    evidence_ids: str
    details: str
    status: str = "success"

class CMMSTicket(SQLModel, table=True):
    id: str = Field(primary_key=True) # e.g. "TICK-2026-001"
    tick: int
    block_id: str
    category: str # "plumbing", "pressure", "water_quality", "meter"
    priority: str = "medium" # "low", "medium", "urgent"
    status: str = "open" # "open", "dispatched", "closed"
    description: str
    assigned_crew: Optional[str] = None
    created_at: datetime = Field(default_factory=get_utc_now)
    resolved_at: Optional[datetime] = None
    cost_inr: float = 0.0

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
