"""
Agent Orchestrator — Phase 4 Core
Runs the continuous autonomous operational loop:
Monitor -> Detect -> Localize -> Forecast -> Prioritize -> Optimize -> Verify -> Intervene

Coordinates the 7 specialized agents, shares a single typed Case repository,
maintains Traces with execution latency in milliseconds, and enforces strict
human-in-the-loop approval gates.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select

from .schemas import Case, Plan, Trace, PrioritizerWeights, ForecastResult
from .monitor import MonitorAgent
from .detector import DetectorAgent
from .localizer import LocalizerAgent
from .forecaster import ForecasterAgent
from .prioritizer import PrioritizerAgent, DEFAULT_WEIGHTS
from .optimizer import OptimizerAgent
from .verifier import Verifier
from .why_generator import WhyGenerator
from .interventor import InterventorMeasurerAgent
from ..db.database import engine, ApprovalItem, AuditLog, get_utc_now

class AgentOrchestrator:
    def __init__(self):
        self.monitor = MonitorAgent()
        self.detector = DetectorAgent()
        self.localizer = LocalizerAgent()
        self.forecaster = ForecasterAgent()
        self.prioritizer = PrioritizerAgent(DEFAULT_WEIGHTS)
        self.optimizer = OptimizerAgent()
        self.verifier = Verifier()
        self.why_generator = WhyGenerator()
        self.interventor = InterventorMeasurerAgent()

        self.active_cases: Dict[str, Case] = {}
        self.traces: List[Trace] = []
        self.latest_forecast: Optional[ForecastResult] = None
        self.latest_plan: Optional[Plan] = None
        self.latest_optimization: Dict[str, Any] = {}

    def run_cycle(self, current_state: Dict[str, Any], complaints: List[Dict[str, Any]] = None, actor_role: str = "agent") -> Dict[str, Any]:
        """
        Executes one full 7-agent pipeline cycle over current simulator telemetry.
        """
        cycle_t0 = time.perf_counter()
        cycle_traces: List[Trace] = []

        # 1. Agent 1: Monitor
        mon_res = self.monitor.run(current_state)
        suspect_sensors = mon_res["suspect_sensors"]
        cycle_traces.append(mon_res["trace"])

        # 2. Agent 2: Detector
        det_res = self.detector.run(current_state, suspect_sensors, complaints)
        detected_cases: List[Case] = det_res["cases"]
        cycle_traces.append(det_res["trace"])

        # Merge newly detected cases into active repository
        for c in detected_cases:
            if c.id not in self.active_cases:
                self.active_cases[c.id] = c

        all_cases = list(self.active_cases.values())

        # 3. Agent 3: Localizer
        loc_res = self.localizer.run(all_cases, current_state)
        cycle_traces.append(loc_res["trace"])

        # 4. Agent 4: Forecaster
        fore_res = self.forecaster.run(current_state)
        self.latest_forecast = fore_res["forecast"]
        cycle_traces.append(fore_res["trace"])

        # 5. Agent 5: Prioritizer
        prio_res = self.prioritizer.run(all_cases, current_state)
        ranked_cases: List[Case] = prio_res["ranked_cases"]
        cycle_traces.append(prio_res["trace"])

        # 6. Agent 6: Optimizer
        opt_res = self.optimizer.run(ranked_cases, current_state)
        self.latest_plan = opt_res["plan"]
        self.latest_optimization = opt_res["lp_solution"]
        cycle_traces.append(opt_res["trace"])

        # 7. Reasoning Text Generation (Why)
        self.why_generator.apply_to_cases(ranked_cases)

        # 8. Verifier (Audits cases, evidence citations, and 2-source rule)
        ver_res = self.verifier.run(ranked_cases)
        cycle_traces.append(ver_res["trace"])

        # 9. Agent 7: Interventor (Dispatches plan or registers in approval queue)
        if self.latest_plan:
            inv_res = self.interventor.dispatch_plan(self.latest_plan, actor_role=actor_role)
            if "trace" in inv_res:
                cycle_traces.append(inv_res["trace"])

        # Record traces
        self.traces.extend(cycle_traces)
        if len(self.traces) > 100:
            self.traces = self.traces[-100:]

        total_ms = round((time.perf_counter() - cycle_t0) * 1000.0, 2)

        return {
            "status": "cycle_completed",
            "cycle_latency_ms": total_ms,
            "active_cases_count": len(self.active_cases),
            "ranked_cases": [c.model_dump() for c in ranked_cases],
            "top_plan": self.latest_plan.model_dump() if self.latest_plan else None,
            "traces": [t.model_dump() for t in cycle_traces]
        }

    def get_cases(self) -> List[Case]:
        return list(self.active_cases.values())

    def get_case(self, case_id: str) -> Optional[Case]:
        return self.active_cases.get(case_id)

    def get_ranked_queue(self) -> List[Dict[str, Any]]:
        sorted_cases = sorted(
            self.active_cases.values(),
            key=lambda c: (c.priority_breakdown.total_score if c.priority_breakdown else 0.0),
            reverse=True
        )
        return [c.model_dump() for c in sorted_cases]

    def set_prioritizer_weights(self, weights: PrioritizerWeights):
        self.prioritizer.set_weights(weights)

    def approve_action(self, approval_id: str, decision: str, note: str, role: str) -> Dict[str, Any]:
        """
        Authorizes or rejects a pending intervention.
        ADMIN ONLY: non-admin gets rejected with status error.
        """
        if role != "admin":
            return {"status": "forbidden", "message": "Only Estate Admin can authorize interventions."}

        with Session(engine) as session:
            item = session.exec(select(ApprovalItem).where(ApprovalItem.id == approval_id)).first()
            if not item:
                # Also check matching plan case id
                item = session.exec(select(ApprovalItem).where(ApprovalItem.id == f"APP-{approval_id}")).first()

            if not item:
                return {"status": "not_found", "message": f"Approval item {approval_id} not found."}

            item.status = "approved" if decision == "approved" else "rejected"
            item.reviewed_by = "Estate Admin"
            item.reviewed_at = get_utc_now()
            session.add(item)

            audit = AuditLog(
                actor="Estate Admin",
                role="admin",
                action_type=f"APPROVAL_{decision.upper()}",
                target_resource=item.id,
                evidence_ids=item.evidence_ids or "",
                details=f"Admin {decision} approval {item.id}. Review note: {note}"
            )
            session.add(audit)
            session.commit()

        # If rejected, remove associated plan from active queue
        if decision == "rejected" and self.latest_plan and (self.latest_plan.case_id in approval_id or approval_id in self.latest_plan.case_id):
            case_id = self.latest_plan.case_id
            if case_id in self.active_cases:
                self.active_cases[case_id].status = "dismissed"
            self.latest_plan = None

        return {
            "status": "ok",
            "approval_id": approval_id,
            "decision": decision,
            "reviewed_by": "Estate Admin",
            "note": note
        }

# Global singleton orchestrator
orchestrator = AgentOrchestrator()
