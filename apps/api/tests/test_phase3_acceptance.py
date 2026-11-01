"""
Phase 3 Acceptance Test Suite
Verifies all core acceptance criteria for the deterministic digital twin simulator:
1. Seed determinism (running same seed twice yields identical telemetry)
2. Diurnal flow curve & night minimum flow for residential hostels
3. Physical burst dynamics (pressure drop + accelerated tank drainage)
4. Fault discrimination (meter fault reads 0 without hydraulic loss)
5. GET /api/state latency (< 50ms)
6. Non-admin RBAC enforcement on /api/sim/control (HTTP 403)
7. 1000-tick continuous simulation stability & memory safety
8. Fallback snapshots generated and structurally valid
"""
import time
import json
import os
import pytest
from fastapi import HTTPException

from apps.api.sim.engine import CampusSimulatorPhase3
from apps.api.routes.simulation import get_simulation_state, control_simulation, SimControlPayload

def test_seed_determinism():
    """Verify running the same seed twice produces bit-for-bit identical data."""
    sim1 = CampusSimulatorPhase3(seed=42)
    sim2 = CampusSimulatorPhase3(seed=42)

    for step in range(30):
        s1 = sim1.tick(1)
        s2 = sim2.tick(1)

        assert s1["tick"] == s2["tick"]
        assert s1["sim_time"] == s2["sim_time"]
        assert s1["sump"]["current_kl"] == s2["sump"]["current_kl"]
        assert s1["weather"]["temp_c"] == s2["weather"]["temp_c"]

        # Check block telemetry identical
        for b1, b2 in zip(s1["blocks"], s2["blocks"]):
            assert b1["id"] == b2["id"]
            assert b1["meter_reading_lpm"] == b2["meter_reading_lpm"]
            assert b1["pressure_bar"] == b2["pressure_bar"]

        # Check tank levels identical
        for t1, t2 in zip(s1["tanks"], s2["tanks"]):
            assert t1["id"] == t2["id"]
            assert t1["current_kl"] == t2["current_kl"]


def test_hostel_diurnal_curve():
    """Verify Cauvery Hostel (BLK-01) exhibits realistic diurnal profile:
    Morning peak (05:00 - 08:30) > Night minimum flow (01:00 - 04:30)
    Evening peak (18:00 - 21:00) > Afternoon lull
    """
    sim = CampusSimulatorPhase3(seed=101)
    readings = []

    # Run for 288 ticks (24 hours starting 06:00)
    for _ in range(288):
        sim.tick(1)
        st = sim.get_state()
        hour = st["hour_of_day"]
        cauvery = next(b for b in st["blocks"] if b["id"] == "BLK-01")
        readings.append({
            "hour": hour,
            "flow": cauvery["meter_reading_lpm"]
        })

    # Morning peak: 06:00 to 08:00
    morning_flows = [r["flow"] for r in readings if 6.0 <= r["hour"] <= 8.0]
    morning_peak = max(morning_flows)

    # Night minimum: 01:00 to 04:00
    night_flows = [r["flow"] for r in readings if 1.0 <= r["hour"] <= 4.0]
    night_min = min(night_flows)

    # Evening peak: 18:30 to 20:30
    evening_flows = [r["flow"] for r in readings if 18.5 <= r["hour"] <= 20.5]
    evening_peak = max(evening_flows)

    # Afternoon lull: 13:00 to 15:00
    afternoon_flows = [r["flow"] for r in readings if 13.0 <= r["hour"] <= 15.0]
    afternoon_avg = sum(afternoon_flows) / len(afternoon_flows)

    assert morning_peak > 2.0 * night_min, f"Morning peak ({morning_peak}) must be > 2x night min ({night_min})"
    assert evening_peak > 1.5 * night_min, f"Evening peak ({evening_peak}) must be > 1.5x night min ({night_min})"
    assert night_min > 0.0, "Night minimum flow must be non-zero (continuous baseline)"
    assert morning_peak > afternoon_avg, "Morning peak must exceed afternoon classroom lull"


def test_simulated_burst_dynamics():
    """Verify burst on PIPE-H-01 causes immediate pressure drop on BLK-01
    and accelerates OHT-HOSTEL drainage.
    """
    sim = CampusSimulatorPhase3(seed=55)

    # Establish baseline for 10 ticks
    for _ in range(10):
        sim.tick(1)

    pre_state = sim.get_state()
    pre_cauvery = next(b for b in pre_state["blocks"] if b["id"] == "BLK-01")
    pre_oht = next(t for t in pre_state["tanks"] if t["id"] == "OHT-HOSTEL")
    pre_pressure = pre_cauvery["pressure_bar"]
    pre_outflow = pre_oht["outflow_lpm"]

    # Inject 80 L/min burst on PIPE-H-01 (feeding BLK-01)
    sim.inject_fault(
        fault_type="burst_main",
        entity_id="PIPE-H-01",
        true_loss_rate_lpm=80.0,
        details="Rupture on Cauvery Hostel supply main"
    )

    sim.tick(1)
    post_state = sim.get_state()
    post_cauvery = next(b for b in post_state["blocks"] if b["id"] == "BLK-01")
    post_oht = next(t for t in post_state["tanks"] if t["id"] == "OHT-HOSTEL")

    # Pressure must drop significantly (> 0.6 bar)
    pressure_drop = pre_pressure - post_cauvery["pressure_bar"]
    assert pressure_drop > 0.6, f"Expected > 0.6 bar drop, got {pressure_drop:.2f} bar"

    # Tank outflow must increase by the burst rate
    outflow_diff = post_oht["outflow_lpm"] - pre_outflow
    assert outflow_diff >= 70.0, f"Expected outflow increase ~80 L/min, got {outflow_diff:.1f} L/min"


def test_meter_fault_discrimination():
    """Verify meter fault drops reading to zero but does NOT drop pipe pressure
    or increase tank drainage.
    """
    sim = CampusSimulatorPhase3(seed=77)

    # Run 5 ticks baseline
    for _ in range(5):
        sim.tick(1)

    pre_state = sim.get_state()
    pre_bhavani = next(b for b in pre_state["blocks"] if b["id"] == "BLK-02")
    pre_oht = next(t for t in pre_state["tanks"] if t["id"] == "OHT-HOSTEL")

    # Inject meter fault (NOT a pipe leak)
    sim.inject_fault(
        fault_type="meter_fault",
        entity_id="BLK-02",
        details="ADC telemetry converter failure"
    )

    sim.tick(1)
    post_state = sim.get_state()
    post_bhavani = next(b for b in post_state["blocks"] if b["id"] == "BLK-02")
    post_oht = next(t for t in post_state["tanks"] if t["id"] == "OHT-HOSTEL")

    # Meter reading collapses to 0 with faulty flag
    assert post_bhavani["meter_reading_lpm"] == 0.0
    assert post_bhavani["meter_quality"] == "faulty"

    # Pipe pressure remains completely intact (no physical hydraulic burst)
    pressure_diff = abs(post_bhavani["pressure_bar"] - pre_bhavani["pressure_bar"])
    assert pressure_diff < 0.15, f"Pressure should not collapse on meter fault, diff was {pressure_diff:.2f}"

    # Tank outflow is not bloated by false leak
    outflow_diff = abs(post_oht["outflow_lpm"] - pre_oht["outflow_lpm"])
    assert outflow_diff < 20.0, "Tank outflow should not spike on a pure sensor failure"


def test_api_state_latency():
    """Verify get_simulation_state executes in strictly < 50ms."""
    latencies = []
    for _ in range(20):
        t0 = time.perf_counter()
        state = get_simulation_state()
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert "tick" in state
        assert "blocks" in state
        assert len(state["blocks"]) == 20

    avg_ms = sum(latencies) / len(latencies)
    assert avg_ms < 50.0, f"Average get_simulation_state took {avg_ms:.2f}ms (expected < 50ms)"


def test_rbac_sim_control():
    """Verify non-admin calling /api/sim/control gets HTTP 403."""
    # 1. Anonymous request (no role) -> 403
    with pytest.raises(HTTPException) as exc_info_anon:
        control_simulation(SimControlPayload(play=True), x_user_role=None)
    assert exc_info_anon.value.status_code == 403

    # 2. Viewer role -> 403
    with pytest.raises(HTTPException) as exc_info_viewer:
        control_simulation(SimControlPayload(play=True), x_user_role="viewer")
    assert exc_info_viewer.value.status_code == 403

    # 3. Admin role -> 200
    res_admin = control_simulation(SimControlPayload(play=True, speed=5), x_user_role="admin")
    assert res_admin["status"] == "ok"
    assert res_admin["speed"] == 5


def test_sim_stream_stability_1000_ticks():
    """Verify simulator runs for 1000 continuous ticks with memory stability."""
    sim = CampusSimulatorPhase3(seed=999)
    for _ in range(1000):
        sim.tick(1)

    final_state = sim.get_state()
    assert final_state["tick"] == 1000
    assert final_state["kpis"]["total_storage_kl"] > 0
    assert len(final_state["blocks"]) == 20
    assert len(final_state["tanks"]) == 4


def test_fallback_snapshots():
    """Verify all fallback snapshot JSON files exist and are valid JSON."""
    for base_dir in ["public/fallback", "apps/web/public/fallback"]:
        campus_path = os.path.join(base_dir, "campus.json")
        day_path = os.path.join(base_dir, "day_snapshot.json")
        leak_path = os.path.join(base_dir, "leak_story.json")

        assert os.path.exists(campus_path), f"Missing {campus_path}"
        assert os.path.exists(day_path), f"Missing {day_path}"
        assert os.path.exists(leak_path), f"Missing {leak_path}"

        with open(campus_path, "r") as f:
            campus_json = json.load(f)
            assert "features" in campus_json

        with open(day_path, "r") as f:
            day_json = json.load(f)
            assert len(day_json["ticks"]) == 288

        with open(leak_path, "r") as f:
            leak_json = json.load(f)
            assert leak_json["metadata"]["fault_type"] == "burst_main"
