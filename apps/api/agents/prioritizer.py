"""
PrioritizerAgent — Agent 5
Scores and ranks all active cases using an explainable, multi-criteria mathematical formula:
Score = w_loss * S_loss + w_pop * S_pop + w_vuln * S_vuln + w_time * S_time + w_cost * S_cost

Never a black box: returns the exact mathematical term breakdown for every case in the queue.
Allows runtime weight adjustments (e.g. from Estate Admin settings).
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from .schemas import Case, PrioritizerWeights, PrioritizerScoreBreakdown, Trace

DEFAULT_WEIGHTS = PrioritizerWeights(
    w_loss=0.30,
    w_pop=0.20,
    w_vuln=0.25,
    w_time=0.15,
    w_cost=0.10
)

class PrioritizerAgent:
    def __init__(self, weights: PrioritizerWeights = DEFAULT_WEIGHTS):
        self.name = "PrioritizerAgent"
        self.weights = weights

    def set_weights(self, new_weights: PrioritizerWeights):
        self.weights = new_weights

    def run(self, cases: List[Case], current_state: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        started_iso = datetime.now(timezone.utc).isoformat()
        notes: List[str] = []

        blocks = {b["id"]: b for b in current_state.get("blocks", [])}
        reserve_hours = current_state.get("kpis", {}).get("reserve_hours", 48.0)

        for case in cases:
            blk = blocks.get(case.location, {})
            pop = blk.get("population", 100)
            is_vuln = blk.get("vulnerable", False)

            # 1. Term 1: Loss Rate (kL/day)
            # Find evidence indicating loss rate or default by case type
            est_loss_lpm = 0.0
            if case.type == "leak":
                for ev in case.evidence:
                    if ev.kind == "mass_imbalance" and ev.value > 0:
                        est_loss_lpm = max(est_loss_lpm, ev.value)
                    elif ev.kind == "night_flow" and ev.value > ev.baseline:
                        est_loss_lpm = max(est_loss_lpm, ev.value - ev.baseline)
                if est_loss_lpm == 0.0:
                    est_loss_lpm = 45.0 # Plausible default for detected leak
            elif case.type == "shortage":
                est_loss_lpm = 25.0

            loss_kld = round((est_loss_lpm * 1440.0) / 1000.0, 2)
            # Normalize to 0-100 (assuming 150 kL/day is catastrophic)
            s_loss = min(100.0, (loss_kld / 150.0) * 100.0)

            # 2. Term 2: People Affected
            # Normalize 0-1000 people to 0-100 scale
            s_pop = min(100.0, (pop / 1000.0) * 100.0)

            # 3. Term 3: Vulnerable Sector Weight
            # Hostels, Health Centre, Daycare have top priority
            s_vuln = 100.0 if is_vuln else 15.0

            # 4. Term 4: Urgency / Time to Critical Level
            # Criticality increases as reserve hours dwindle below 48 hours
            urgency_factor = max(0.0, 1.0 - (min(48.0, reserve_hours) / 48.0))
            s_time = round(urgency_factor * 100.0, 1)

            # 5. Term 5: Repair Cost & Crew Factor
            # Leaks with high loss rate have urgent crew assigned (score 85 vs 40)
            s_cost = 85.0 if case.type == "leak" and est_loss_lpm > 30.0 else 45.0

            # Compute weighted total
            w = self.weights
            total_score = round(
                w.w_loss * s_loss +
                w.w_pop * s_pop +
                w.w_vuln * s_vuln +
                w.w_time * s_time +
                w.w_cost * s_cost,
                2
            )

            breakdown = PrioritizerScoreBreakdown(
                total_score=total_score,
                loss_rate_score=round(s_loss, 2),
                people_score=round(s_pop, 2),
                vulnerable_score=round(s_vuln, 2),
                urgency_reserve_score=round(s_time, 2),
                cost_crew_score=round(s_cost, 2),
                weights_applied={
                    "w_loss": w.w_loss,
                    "w_pop": w.w_pop,
                    "w_vuln": w.w_vuln,
                    "w_time": w.w_time,
                    "w_cost": w.w_cost
                },
                details={
                    "estimated_loss_kld": loss_kld,
                    "population": pop,
                    "is_vulnerable": is_vuln,
                    "reserve_hours": reserve_hours
                }
            )

            case.priority_breakdown = breakdown
            notes.append(f"Scored {case.id} [{case.location}]: {total_score} points")

        # Sort active cases by total priority score descending
        cases.sort(key=lambda c: (c.priority_breakdown.total_score if c.priority_breakdown else 0.0), reverse=True)

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ended_iso = datetime.now(timezone.utc).isoformat()

        trace = Trace(
            agent=self.name,
            started=started_iso,
            ended=ended_iso,
            ms=elapsed_ms,
            inputs=[{
                "cases_ranked": len(cases),
                "weights": {
                    "w_loss": self.weights.w_loss,
                    "w_pop": self.weights.w_pop,
                    "w_vuln": self.weights.w_vuln,
                    "w_time": self.weights.w_time,
                    "w_cost": self.weights.w_cost
                }
            }],
            outputs=[{
                "top_ranked_case": cases[0].id if cases else None,
                "top_score": cases[0].priority_breakdown.total_score if (cases and cases[0].priority_breakdown) else 0.0
            }],
            notes=notes
        )

        return {
            "ranked_cases": cases,
            "trace": trace
        }
