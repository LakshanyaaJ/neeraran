"""
Pydantic Schemas for NEERARAN Agent Core — Phase 4
Defines shared typed objects: Evidence, Case, Plan, Trace, and auxiliary types.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    id: str = Field(..., description="Unique evidence ID, e.g., EVID-01-MNF")
    kind: str = Field(..., description="night_flow, pressure_drop, mass_imbalance, tank_drawdown, complaint, sensor_anomaly")
    source: str = Field(..., description="Sensor, telemetry stream, or user complaint ID")
    block_or_node: str = Field(..., description="Entity ID e.g. BLK-01, PIPE-H-01, OHT-HOSTEL")
    tick_range: List[int] = Field(default_factory=list, description="[start_tick, end_tick]")
    value: float = Field(..., description="Observed numeric reading")
    baseline: float = Field(..., description="Expected baseline or threshold")
    unit: str = Field("L/min", description="Measurement unit")
    note: str = Field(..., description="Human-readable explanation of the evidence")
    timestamp: Optional[str] = None

class PlanStep(BaseModel):
    order: int
    tool: str = Field(..., description="create_cmms_ticket, set_valve, set_pump_schedule, draft_advisory, notify")
    args: Dict[str, Any]
    reason: str
    target_entity: str

class RollbackAction(BaseModel):
    tool: str
    args: Dict[str, Any]
    description: str

class ExpectedImpact(BaseModel):
    litres_saved_per_day: float = 0.0
    rupees_saved_per_day: float = 0.0
    reserve_hours_gained: float = 0.0
    repair_time_hours_avoided: float = 0.0
    people_protected: int = 0

class Plan(BaseModel):
    case_id: str
    steps: List[PlanStep] = Field(default_factory=list)
    expected_impact: ExpectedImpact
    risk: str = "low" # "low", "medium", "high"
    needs_approval: bool = False
    vulnerable_flag: bool = False
    equity_check: Optional[str] = None
    rollback: Optional[RollbackAction] = None
    created_at: Optional[str] = None

class PrioritizerScoreBreakdown(BaseModel):
    total_score: float
    loss_rate_score: float
    people_score: float
    vulnerable_score: float
    urgency_reserve_score: float
    cost_crew_score: float
    weights_applied: Dict[str, float]
    details: Dict[str, Any]

class Case(BaseModel):
    id: str = Field(..., description="CASE-YYYYMMDD-XXX")
    type: str = Field(..., description="leak, shortage, demand_spike, sensor_fault, quality")
    location: str = Field(..., description="Block or pipe ID")
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: str = Field("detected", description="detected, investigating, actionable, in_progress, resolved, dismissed")
    evidence: List[Evidence] = Field(default_factory=list)
    why_text: str = ""
    groundedness_score: float = 1.0
    verifier_notes: List[str] = Field(default_factory=list)
    plan: Optional[Plan] = None
    priority_breakdown: Optional[PrioritizerScoreBreakdown] = None
    top_candidate_segments: List[Dict[str, Any]] = Field(default_factory=list)
    created_tick: int = 0
    updated_at: Optional[str] = None

class Trace(BaseModel):
    agent: str = Field(..., description="Monitor, Detector, Localizer, Forecaster, Prioritizer, Optimizer, Interventor")
    started: str
    ended: str
    ms: float
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

class ForecastResult(BaseModel):
    block_forecast_7d: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    tank_levels_72h: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict)
    days_of_reserve: float = 0.0
    reserve_80pct_lower: float = 0.0
    reserve_80pct_upper: float = 0.0
    model_mae: float = 0.0
    baseline_naive_mae: float = 0.0
    comparison_summary: str = ""

class PrioritizerWeights(BaseModel):
    w_loss: float = 0.30
    w_pop: float = 0.20
    w_vuln: float = 0.25
    w_time: float = 0.15
    w_cost: float = 0.10
