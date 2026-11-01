"""
MonitorAgent — Agent 1
Reads latest telemetry ticks, verifies data quality (stale, flat-line zero, out of range, dropouts).
Flags suspect sensors so downstream agents do not misdiagnose sensor failures as physical leaks.
"""
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from .schemas import Evidence, Trace

class MonitorAgent:
    def __init__(self):
        self.name = "MonitorAgent"
        self.history_buffer: Dict[str, List[float]] = {}
        self.suspect_sensors: Dict[str, str] = {}

    def run(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        t0 = time.perf_counter()
        started_iso = datetime.now(timezone.utc).isoformat()
        evidence_list: List[Evidence] = []
        notes: List[str] = []
        self.suspect_sensors.clear()

        tick = current_state.get("tick", 0)

        # Inspect all campus block meters
        for blk in current_state.get("blocks", []):
            b_id = blk["id"]
            flow = blk.get("meter_reading_lpm", 0.0)
            quality = blk.get("meter_quality", "good")

            # Update historical sliding buffer for this block
            if b_id not in self.history_buffer:
                self.history_buffer[b_id] = []
            self.history_buffer[b_id].append(flow)
            if len(self.history_buffer[b_id]) > 12:
                self.history_buffer[b_id].pop(0)

            # Check 1: Explicit sensor dropout
            if quality == "dropout":
                self.suspect_sensors[b_id] = "sensor_dropout"
                ev = Evidence(
                    id=f"EVID-{b_id}-DROPOUT",
                    kind="sensor_anomaly",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[max(0, tick - 3), tick],
                    value=0.0,
                    baseline=blk.get("base_lpm", 20.0),
                    unit="L/min",
                    note=f"Hardware communication dropout flagged by sensor bus for {blk['name']}."
                )
                evidence_list.append(ev)
                notes.append(f"Sensor dropout on {b_id}")

            # Check 2: Out of range (< 0 or > 600 L/min for a standard campus block)
            elif flow < 0.0 or flow > 600.0:
                self.suspect_sensors[b_id] = "out_of_range"
                ev = Evidence(
                    id=f"EVID-{b_id}-OOR",
                    kind="sensor_anomaly",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[tick, tick],
                    value=flow,
                    baseline=blk.get("base_lpm", 20.0),
                    unit="L/min",
                    note=f"Meter readout of {flow:.1f} L/min exceeds physical hydraulic bounds (0-600 L/min)."
                )
                evidence_list.append(ev)
                notes.append(f"Out of range reading on {b_id}: {flow} L/min")

            # Check 3: Flatline zero or frozen identical reading
            elif quality == "faulty" or (flow == 0.0 and blk.get("population", 0) > 100):
                self.suspect_sensors[b_id] = "flatline_zero"
                ev = Evidence(
                    id=f"EVID-{b_id}-FLATLINE",
                    kind="sensor_anomaly",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[max(0, tick - 6), tick],
                    value=0.0,
                    baseline=blk.get("base_lpm", 20.0),
                    unit="L/min",
                    note=f"Digital telemetry display flatlining at zero despite {blk['population']} residents present."
                )
                evidence_list.append(ev)
                notes.append(f"Flatline zero suspect sensor on {b_id}")

            # Check 4: Stale frozen buffer (same float value for 6 consecutive ticks)
            buf = self.history_buffer[b_id]
            if len(buf) >= 6 and all(abs(x - buf[0]) < 0.001 for x in buf) and buf[0] > 0.0:
                self.suspect_sensors[b_id] = "stale_frozen"
                ev = Evidence(
                    id=f"EVID-{b_id}-STALE",
                    kind="sensor_anomaly",
                    source=f"meter:{b_id}",
                    block_or_node=b_id,
                    tick_range=[max(0, tick - 6), tick],
                    value=buf[0],
                    baseline=blk.get("base_lpm", 20.0),
                    unit="L/min",
                    note=f"Telemetry frozen at exactly {buf[0]:.2f} L/min without natural hydraulic turbulence."
                )
                evidence_list.append(ev)
                notes.append(f"Stale telemetry sensor on {b_id}")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ended_iso = datetime.now(timezone.utc).isoformat()

        trace = Trace(
            agent=self.name,
            started=started_iso,
            ended=ended_iso,
            ms=elapsed_ms,
            inputs=[{"tick": tick, "blocks_checked": len(current_state.get("blocks", []))}],
            outputs=[{
                "suspect_sensors_count": len(self.suspect_sensors),
                "suspect_sensors": self.suspect_sensors,
                "evidence_count": len(evidence_list)
            }],
            notes=notes
        )

        return {
            "suspect_sensors": self.suspect_sensors,
            "evidence": evidence_list,
            "trace": trace
        }

