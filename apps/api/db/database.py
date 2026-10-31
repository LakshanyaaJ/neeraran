"""
SQLModel database setup for NEERARAN audit logging and approval queue.
Stored locally in SQLite.
"""
from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Session, create_engine, select

DATABASE_URL = "sqlite:///./apps/api/neeraran.db"
engine = create_engine(DATABASE_URL, echo=False)

def get_utc_now():
    return datetime.now(timezone.utc)

class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=get_utc_now)
    actor: str # e.g. "Estate Admin", "System Autonomous Agent"
    role: str # "admin", "viewer", "agent"
    action_type: str # "APPROVE_PLAN", "REJECT_PLAN", "OVERRIDE_VALVE", "INJECT_SCENARIO"
    target_resource: str # e.g. "VALVE-04", "PLAN-STEP-02", "OHT-HOSTEL"
    evidence_ids: str # comma separated: "EVID-PRS-4029, EVID-MET-104"
    details: str
    status: str = "success"

class ApprovalItem(SQLModel, table=True):
    id: str = Field(primary_key=True) # e.g. "REQ-2026-001"
    title: str
    description: str
    category: str # "pressure_modulation", "zone_rationing", "pump_dispatch", "emergency_shutoff"
    is_vulnerable: bool = False
    equity_impact_check: str # Plain-text audit description of impact on vulnerable blocks
    proposed_actions: str # JSON string of steps
    rollback_step: str # JSON string of rollback action
    evidence_ids: str # comma separated: "EVID-PRS-4029, EVID-HST-22"
    created_at: datetime = Field(default_factory=get_utc_now)
    status: str = "pending" # "pending", "approved", "rejected"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

def init_db():
    SQLModel.metadata.create_all(engine)
    # Seed initial approval items and audit logs if empty
    with Session(engine) as session:
        existing = session.exec(select(ApprovalItem)).first()
        if not existing:
            demo_approval = ApprovalItem(
                id="REQ-8021",
                title="Modulate Pressure on Supply Branch L-2 (Vaigai Hostel Feed)",
                description="Reduce line pressure from 2.45 bar to 1.80 bar between 01:00 - 05:00 to curtail nocturnal joint weepage pending morning gasket overhaul.",
                category="pressure_modulation",
                is_vulnerable=True,
                equity_impact_check="PASS: Minimum dynamic head at top floor sinks remains at 1.45 bar. Vaigai Hostel buffer tank maintains 82 kL (over 18 hrs reserve). Crèche and Clinic are fed via independent Trunk A-1 and remain unaffected.",
                proposed_actions='[{"step": 1, "tool": "SCADA_VALVE_COMMAND", "target": "VALVE-03-VGH", "param": "throttle_65pct", "evidence": "EVID-PRS-4029"}]',
                rollback_step='{"tool": "SCADA_VALVE_COMMAND", "target": "VALVE-03-VGH", "param": "open_100pct", "trigger": "pressure_below_1.2_bar"}',
                evidence_ids="EVID-PRS-4029, EVID-REP-1104",
                created_at=get_utc_now(),
                status="pending"
            )
            session.add(demo_approval)
            session.commit()

        existing_audit = session.exec(select(AuditLog)).first()
        if not existing_audit:
            audit = AuditLog(
                actor="System Bootstrapper",
                role="agent",
                action_type="INITIALIZE_SIMULATION",
                target_resource="CAMPUS_DIGITAL_TWIN",
                evidence_ids="EVID-SYS-BOOT",
                details="Digital twin initialized with seed 42, 20 blocks, 4 OHTs, 2 borewells, 1 sump.",
                status="success"
            )
            session.add(audit)
            session.commit()

def get_session():
    with Session(engine) as session:
        yield session
