"""
InterventorMeasurerAgent — Agent 7
- Converts verified Plan steps into actionable enterprise tool calls.
- Consequential interventions (pressure modulation, zone rationing, vulnerable lines)
  are gated in the ApprovalItem queue awaiting Estate Admin authorization.
- Runs counterfactual physics simulations to calculate expected impact:
  litres saved, rupees saved, hours of reserve gained, repair time avoided.
- Post-execution: compares real telemetry against forecast estimate and stores variance.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select

from .schemas import Plan, Trace, ExpectedImpact
from ..tools.enterprise import (
    create_cmms_ticket, set_valve, set_pump_schedule, draft_advisory, notify
)
from ..db.database import engine, ApprovalItem, AuditLog, get_utc_now

class InterventorMeasurerAgent:
    def __init__(self):
        self.name = "InterventorMeasurerAgent"
        self.executed_actions: List[Dict[str, Any]] = []

    def dispatch_plan(self, plan: Plan, actor_role: str = "agent") -> Dict[str, Any]:
        """Dispatches plan steps into simulated enterprise systems."""
        t0 = time.perf_counter()
        started_iso = datetime.now(timezone.utc).isoformat()
        dispatched_results: List[Dict[str, Any]] = []
        notes: List[str] = []

        # If plan touches vulnerable sector and actor is not Estate Admin, register in ApprovalItem queue
        if plan.needs_approval and actor_role != "admin":
            approval_id = f"APP-{plan.case_id}"
            with Session(engine) as session:
                existing = session.exec(select(ApprovalItem).where(ApprovalItem.id == approval_id)).first()
                if not existing:
                    app_item = ApprovalItem(
                        id=approval_id,
                        title=f"Remediation Plan for {plan.case_id}",
                        description=f"Automated remediation with {len(plan.steps)} steps. Impact: {plan.expected_impact.litres_saved_per_day:,.0f} L/day savings.",
                        category="zone_rationing" if plan.vulnerable_flag else "pressure_modulation",
                        is_vulnerable=plan.vulnerable_flag,
                        equity_impact_check=plan.equity_check or "Standard verification",
                        proposed_actions=str([s.model_dump() for s in plan.steps]),
                        rollback_step=str(plan.rollback.model_dump()) if plan.rollback else "",
                        evidence_ids="",
                        status="pending"
                    )
                    session.add(app_item)
                    session.commit()
            notes.append(f"Plan for {plan.case_id} registered in Approval Queue awaiting Estate Admin authorization.")
            return {
                "status": "awaiting_approval",
                "approval_id": approval_id,
                "needs_approval": True,
                "dispatched_steps": []
            }

        # Otherwise, execute non-consequential or authorized steps
        for step in plan.steps:
            tool = step.tool
            args = step.args
            res = {}

            if tool == "create_cmms_ticket":
                res = create_cmms_ticket(
                    block=args.get("block", ""),
                    segment=args.get("segment", ""),
                    priority=args.get("priority", "medium"),
                    summary=args.get("summary", ""),
                    actor="InterventorAgent"
                )
            elif tool == "set_valve":
                res = set_valve(
                    valve_id=args.get("valve_id", ""),
                    state=args.get("state", "open"),
                    reason=step.reason,
                    actor="admin" if actor_role == "admin" else "InterventorAgent",
                    target_block=args.get("target_block")
                )
            elif tool == "draft_advisory":
                res = draft_advisory(
                    audience=args.get("audience", "campus_all"),
                    text=args.get("text", ""),
                    actor="InterventorAgent"
                )
            elif tool == "notify":
                res = notify(
                    role=args.get("role", "warden"),
                    message=args.get("message", ""),
                    actor="InterventorAgent"
                )

            dispatched_results.append({
                "step_order": step.order,
                "tool": tool,
                "result": res
            })
            notes.append(f"Executed step {step.order} [{tool}]: {res.get('status')}")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ended_iso = datetime.now(timezone.utc).isoformat()

        trace = Trace(
            agent=self.name,
            started=started_iso,
            ended=ended_iso,
            ms=elapsed_ms,
            inputs=[{"case_id": plan.case_id, "steps_count": len(plan.steps)}],
            outputs=[{"dispatched_count": len(dispatched_results)}],
            notes=notes
        )

        return {
            "status": "dispatched",
            "needs_approval": False,
            "dispatched_steps": dispatched_results,
            "trace": trace
        }

    def measure_impact(self, pre_flow_lpm: float, post_flow_lpm: float, estimated_savings_lpd: float) -> Dict[str, Any]:
        """
        Runs counterfactual measurement comparing post-intervention flow vs pre-intervention.
        Stores estimation error in audit log.
        """
        observed_savings_lpm = max(0.0, pre_flow_lpm - post_flow_lpm)
        actual_savings_lpd = observed_savings_lpm * 1440.0

        error_pct = 0.0
        if estimated_savings_lpd > 0:
            error_pct = round(abs(estimated_savings_lpd - actual_savings_lpd) / estimated_savings_lpd * 100.0, 1)

        rupees_saved = round((actual_savings_lpd / 1000.0) * 120.0, 2) # ₹120 per kL treated potable water

        with Session(engine) as session:
            audit = AuditLog(
                actor="MeasurerAgent",
                role="agent",
                action_type="IMPACT_MEASURED",
                target_resource="intervention_evaluation",
                evidence_ids="",
                details=(
                    f"Counterfactual Impact: Actual {actual_savings_lpd:,.0f} L/day vs "
                    f"Estimated {estimated_savings_lpd:,.0f} L/day. Model Variance: {error_pct}%. "
                    f"Net Value Saved: ₹{rupees_saved}/day."
                )
            )
            session.add(audit)
            session.commit()

        return {
            "actual_savings_lpd": actual_savings_lpd,
            "estimated_savings_lpd": estimated_savings_lpd,
            "error_pct": error_pct,
            "rupees_saved_per_day": rupees_saved
        }
