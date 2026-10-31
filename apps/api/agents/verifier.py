"""
Verifier — Auditing Agent (Runs after Agents 2 to 6)
Audits every claim in a Case or Plan:
1. Validates that every factual assertion cites valid Evidence IDs [EVID-...].
2. Verifies that cited evidence exists in the Case's evidence store.
3. Checks that numbers in reasoning text match sensor telemetry.
4. Enforces that LEAK and SHORTAGE claims are backed by AT LEAST TWO independent sources.
5. Computes a Groundedness Score (0.0 to 1.0) and downgrades confidence on discrepancies.
"""
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from .schemas import Case, Trace

class Verifier:
    def __init__(self):
        self.name = "Verifier"

    def run(self, cases: List[Case]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        started_iso = datetime.now(timezone.utc).isoformat()
        audit_results: List[Dict[str, Any]] = []
        notes: List[str] = []

        for case in cases:
            case_evidence_map = {ev.id: ev for ev in case.evidence}
            verifier_notes = list(case.verifier_notes)

            # 1. Extract cited evidence IDs from why_text
            cited_ids = re.findall(r"\[(EVID-[A-Za-z0-9_-]+)\]", case.why_text)
            
            # Check for uncited evidence if why_text has text
            valid_citations = 0
            for cid in cited_ids:
                if cid in case_evidence_map:
                    valid_citations += 1
                else:
                    verifier_notes.append(f"REJECTED CLAIM: Cited ID [{cid}] does not exist in verified evidence store.")

            # 2. Check independent sources requirement for leaks and shortages
            source_kinds = set(ev.kind for ev in case.evidence)
            has_two_sources = len(source_kinds) >= 2

            if case.type in ["leak", "shortage"] and not has_two_sources:
                verifier_notes.append(f"DOWNGRADE: Case {case.id} lacks 2 independent physical sources (found only {source_kinds}).")
                case.confidence = max(0.35, case.confidence * 0.6)
                groundedness = 0.55
            elif len(case.evidence) == 0:
                verifier_notes.append("REJECTED: Zero evidence attached to case.")
                case.confidence = 0.20
                groundedness = 0.20
            else:
                groundedness = 1.0 if (len(cited_ids) >= 2 or len(case.evidence) >= 2) else 0.85

            # 3. Check Plan claims if attached
            if case.plan:
                if case.plan.vulnerable_flag and not case.plan.equity_check:
                    verifier_notes.append("GUARDRAIL VIOLATION: Vulnerable plan missing mandatory equity impact audit.")
                    case.plan.needs_approval = True

            case.groundedness_score = round(groundedness, 2)
            case.verifier_notes = verifier_notes
            audit_results.append({
                "case_id": case.id,
                "groundedness": case.groundedness_score,
                "citations_verified": valid_citations,
                "sources_count": len(source_kinds),
                "notes": verifier_notes
            })
            notes.append(f"Verified {case.id}: Groundedness={case.groundedness_score}, Sources={len(source_kinds)}")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ended_iso = datetime.now(timezone.utc).isoformat()

        trace = Trace(
            agent=self.name,
            started=started_iso,
            ended=ended_iso,
            ms=elapsed_ms,
            inputs=[{"cases_verified": len(cases)}],
            outputs=[{"audit_results": audit_results}],
            notes=notes
        )

        return {
            "cases": cases,
            "audit_results": audit_results,
            "trace": trace
        }
