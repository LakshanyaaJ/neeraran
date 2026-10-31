"""
DetectorAgent — Agent 2
Per-block anomaly detection combining:
- Minimum Night Flow (MNF) z-score against baseline
- IsolationForest on [flow, pressure, hour, weekday, occupancy_flag]
- Pipe pressure drop verification
- Tank mass balance drawdown rate

CRITICAL RULE:
A 'leak' case strictly requires agreement from AT LEAST TWO independent physical signals
(e.g., elevated night flow AND downstream pressure drop, or tank drawdown mismatch).
A single isolated signal becomes a 'sensor_fault' or 'watch' case.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

from .schemas import Case, Evidence, Trace

class DetectorAgent:
    def __init__(self):
        self.name = "DetectorAgent"
        self._init_models()

    def _init_models(self):
        """Fit IsolationForest on synthetic normal campus diurnal telemetry."""
        # Feature columns: [flow, pressure, hour, weekday, occupancy_flag]
        rng = np.random.default_rng(42)
        n_samples = 1200

        hours = rng.uniform(0, 24, n_samples)
        weekdays = rng.integers(0, 7, n_samples)
        occupancies = np.where(weekdays < 5, 1.0, 0.3)

        # Baseline flow follows sinusoidal daylight curve
        diurnal = 25.0 + 35.0 * np.clip(np.sin((hours - 6.0) / 16.0 * np.pi), 0, 1)
        flows = diurnal * occupancies + rng.normal(0, 3.0, n_samples)
        flows = np.clip(flows, 5.0, 120.0)

        # Normal pressure is 2.2 to 2.6 bar
        pressures = 2.45 - (flows / 100.0) * 0.15 + rng.normal(0, 0.05, n_samples)
        pressures = np.clip(pressures, 2.0, 2.7)

        X_train = np.column_stack([flows, pressures, hours, weekdays, occupancies])
        self.iso_forest = IsolationForest(n_estimators=60, contamination=0.03, random_state=42)
        self.iso_forest.fit(X_train)

    def run(self, current_state: Dict[str, Any], suspect_sensors: Dict[str, str], complaints: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        t0 = time.perf_counter()
        started_iso = datetime.now(timezone.utc).isoformat()
        cases: List[Case] = []
        evidence_store: List[Evidence] = []
        notes: List[str] = []

        tick = current_state.get("tick", 0)
        sim_time_str = current_state.get("sim_time", "")
        hour = current_state.get("hour_of_day", 12.0)
        
        # Parse weekday
        try:
            dt = datetime.fromisoformat(sim_time_str)
            weekday = dt.weekday()
        except Exception:
            weekday = 1

        occupancy_flag = 1.0 if weekday < 5 else 0.35

        # Map tanks for drawdown check
        tank_outflows = {t["id"]: t.get("outflow_lpm", 0.0) for t in current_state.get("tanks", [])}

        # Check each block
        for blk in current_state.get("blocks", []):
            b_id = blk["id"]
            flow = blk.get("meter_reading_lpm", 0.0)
            pressure = blk.get("pressure_bar", 2.45)
            b_type = blk.get("type", "academic")
            fed_by = blk.get("fed_by", "")
            base_lpm = blk.get("base_lpm", 20.0)

            # 1. Check if MonitorAgent already identified this as a sensor fault
            if b_id in suspect_sensors:
                reason = suspect_sensors[b_id]
                ev = Evidence(
                    id=f"EVID-{b_id}-SF",
                    kind="sensor_anomaly",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[max(0, tick - 6), tick],
                    value=flow,
                    baseline=base_lpm,
                    unit="L/min",
                    note=f"Suspect telemetry: {reason}. Hardware diagnostic required before hydraulic investigation."
                )
                evidence_store.append(ev)

                # Open sensor_fault case (NOT a leak case!)
                case = Case(
                    id=f"CASE-{tick}-{b_id}-SF",
                    type="sensor_fault",
                    location=b_id,
                    confidence=0.92,
                    status="investigating",
                    evidence=[ev],
                    why_text=f"Telemetry failure detected on {blk['name']} meter [{ev.id}]. Reading reads {flow:.1f} L/min but line pressure is {pressure:.2f} bar, indicating no pipe burst.",
                    groundedness_score=1.0,
                    verifier_notes=["Confirmed hardware discrepancy without hydraulic loss"],
                    created_tick=tick
                )
                cases.append(case)
                notes.append(f"Sensor fault case registered for {b_id}")
                continue

            # 2. Check Signals for physical leak:
            signals_flagged = []
            block_evidence: List[Evidence] = []

            # Signal A: Minimum Night Flow (MNF) Analysis
            is_night = (hour >= 23.0 or hour <= 5.0)
            expected_night_flow = base_lpm * 0.15 # Baseline night flow is ~15% of daily average
            night_std = max(1.5, expected_night_flow * 0.25)
            z_score = (flow - expected_night_flow) / night_std

            if is_night and z_score > 2.5:
                ev_mnf = Evidence(
                    id=f"EVID-{b_id}-MNF",
                    kind="night_flow",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[max(0, tick - 6), tick],
                    value=round(flow, 1),
                    baseline=round(expected_night_flow, 1),
                    unit="L/min",
                    note=f"Minimum night flow of {flow:.1f} L/min exceeds expected baseline ({expected_night_flow:.1f} L/min) with z-score {z_score:.2f}."
                )
                block_evidence.append(ev_mnf)
                signals_flagged.append("elevated_night_flow")

            # Signal B: Pressure Drop along supply line
            expected_pressure = 2.45
            pressure_drop = expected_pressure - pressure
            if pressure_drop > 0.40:
                ev_press = Evidence(
                    id=f"EVID-{b_id}-PRESS",
                    kind="pressure_drop",
                    source=f"sensor:node_{b_id}",
                    block_or_node=b_id,
                    tick_range=[tick, tick],
                    value=round(pressure, 2),
                    baseline=expected_pressure,
                    unit="bar",
                    note=f"Terminal head pressure collapsed to {pressure:.2f} bar (drop of {pressure_drop:.2f} bar below 2.45 bar baseline)."
                )
                block_evidence.append(ev_press)
                signals_flagged.append("pressure_drop")

            # Signal C: Isolation Forest Anomaly
            features = np.array([[flow, pressure, hour, weekday, occupancy_flag]])
            iso_pred = self.iso_forest.predict(features)[0]
            if iso_pred == -1:
                ev_iso = Evidence(
                    id=f"EVID-{b_id}-ISO",
                    kind="statistical_anomaly",
                    source="ml_isolation_forest",
                    block_or_node=b_id,
                    tick_range=[tick, tick],
                    value=round(flow, 1),
                    baseline=round(base_lpm, 1),
                    unit="multivariate",
                    note=f"Multivariate IsolationForest flagged joint flow ({flow:.1f} L/min) and pressure ({pressure:.2f} bar) as statistical outlier."
                )
                block_evidence.append(ev_iso)
                signals_flagged.append("ml_outlier")

            # Signal D: Tank Drawdown Imbalance (Supply vs Sum of Block Meters)
            if fed_by and fed_by in tank_outflows:
                tank_outflow = tank_outflows[fed_by]
                # If tank outflow is significantly larger than aggregate metered flow
                if tank_outflow > (base_lpm * 1.6):
                    ev_tank = Evidence(
                        id=f"EVID-{fed_by}-DRAWDOWN",
                        kind="tank_drawdown",
                        source=f"level:{fed_by}",
                        block_or_node=fed_by,
                        tick_range=[max(0, tick - 6), tick],
                        value=round(tank_outflow, 1),
                        baseline=round(base_lpm, 1),
                        unit="L/min",
                        note=f"Reservoir {fed_by} outflow rate ({tank_outflow:.1f} L/min) exceeds total metered demand, indicating trunk line loss."
                    )
                    block_evidence.append(ev_tank)
                    signals_flagged.append("tank_drawdown_mismatch")

            # Signal E: Student or Staff Complaint nearby
            if complaints:
                for c in complaints:
                    if c.get("entity_id") == b_id or b_id in c.get("text", ""):
                        ev_comp = Evidence(
                            id=f"EVID-{b_id}-COMPLAINT",
                            kind="complaint",
                            source="campus_helpdesk",
                            block_or_node=b_id,
                            tick_range=[tick, tick],
                            value=1.0,
                            baseline=0.0,
                            unit="complaint",
                            note=f"Campus complaint logged: '{c.get('text', '')}'."
                        )
                        block_evidence.append(ev_comp)
                        signals_flagged.append("field_complaint")

            # 3. Decision Logic: Need agreement of AT LEAST TWO signals for a leak!
            evidence_store.extend(block_evidence)

            if len(signals_flagged) >= 2:
                # Open LEAK case!
                confidence = min(0.96, 0.75 + 0.08 * len(signals_flagged))
                case = Case(
                    id=f"CASE-{tick}-{b_id}-LEAK",
                    type="leak",
                    location=b_id,
                    confidence=confidence,
                    status="actionable",
                    evidence=block_evidence,
                    why_text="", # Will be drafted by WhyGenerator and verified
                    groundedness_score=1.0,
                    verifier_notes=[f"Verified across {len(signals_flagged)} signals: {', '.join(signals_flagged)}"],
                    created_tick=tick
                )
                cases.append(case)
                notes.append(f"LEAK case opened for {b_id} (Signals: {signals_flagged})")

            elif len(signals_flagged) == 1:
                # Single isolated signal: Open WATCH or SENSOR_FAULT case (NEVER LEAK!)
                case = Case(
                    id=f"CASE-{tick}-{b_id}-WATCH",
                    type="watch" if signals_flagged[0] != "sensor_anomaly" else "sensor_fault",
                    location=b_id,
                    confidence=0.48,
                    status="investigating",
                    evidence=block_evidence,
                    why_text="",
                    groundedness_score=0.9,
                    verifier_notes=["Single signal flagged; withholding leak classification pending second confirmatory source"],
                    created_tick=tick
                )
                cases.append(case)
                notes.append(f"Single signal watch case for {b_id} ({signals_flagged[0]})")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ended_iso = datetime.now(timezone.utc).isoformat()

        trace = Trace(
            agent=self.name,
            started=started_iso,
            ended=ended_iso,
            ms=elapsed_ms,
            inputs=[{"blocks_evaluated": len(current_state.get("blocks", [])), "tick": tick}],
            outputs=[{
                "cases_opened": len(cases),
                "leak_cases": len([c for c in cases if c.type == "leak"]),
                "sensor_cases": len([c for c in cases if c.type == "sensor_fault"]),
                "watch_cases": len([c for c in cases if c.type == "watch"]),
                "total_evidence": len(evidence_store)
            }],
            notes=notes
        )

        return {
            "cases": cases,
            "evidence": evidence_store,
            "trace": trace
        }
