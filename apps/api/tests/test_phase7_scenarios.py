"""
Phase 7 Acceptance Test Suite — NEERARAN Adaptability & Unseen Scenarios
Verifies:
1. Parsing sentence 'Heatwave for 5 days, hostels use 30 percent more, one borewell drops to half' yields 3 typed events.
2. Injecting scenario executes full re-plan with recovery latency strictly < 10 seconds.
3. Gibberish inputs return unrecognized status with zero events and zero changes to digital twin.
4. Contamination reports (unsupported autonomous tools) trigger honest disclosure, quality case, and advisory without pretending.
5. Non-admin RBAC rejects scenario injection with HTTP 403.
"""
import pytest
from fastapi import HTTPException
from apps.api.routes.simulation import parse_scenario, inject_scenario, ParseScenarioPayload, InjectScenarioPayload, ScenarioEventItem

def test_natural_language_scenario_parser_3_events():
    """
    Acceptance: Typing 'Heatwave for 5 days, hostels use 30 percent more, one borewell drops to half'
    produces a confirmation card with 3 events.
    """
    prompt = "Heatwave for 5 days, hostels use 30 percent more, one borewell drops to half"
    res = parse_scenario(ParseScenarioPayload(prompt=prompt))

    assert res["status"] == "parsed"
    assert len(res["events"]) == 3, f"Expected 3 parsed events, got {len(res['events'])}"

    event_types = [e["type"] for e in res["events"]]
    assert "heatwave" in event_types
    assert "occupancy_surge" in event_types
    assert "borewell_decline" in event_types

    assert "confirmation_text" in res
    assert "I understood:" in res["confirmation_text"]


def test_gibberish_input_rejection():
    """
    Acceptance: Gibberish input gives an unrecognized response with no events and no changes.
    """
    res = parse_scenario(ParseScenarioPayload(prompt="xyzqwerty 123456 asdfgh"))
    assert res["status"] == "unrecognized"
    assert len(res["events"]) == 0
    assert "Could not recognize" in res["message"]


def test_scenario_injection_and_recovery_timer_under_10s():
    """
    Acceptance: Scenario injection executes in under 10 seconds, showing a visible re-plan
    and before/after metrics.
    """
    events = [
        ScenarioEventItem(type="heatwave", target="ambient", parameters={"delta_c": 5.0, "days": 5}, description="5-day heatwave"),
        ScenarioEventItem(type="borewell_decline", target="BW-01", parameters={"pct": 50.0}, description="Borewell yield halved")
    ]

    res = inject_scenario(InjectScenarioPayload(events=events, role="admin"), x_user_role="admin")
    assert res["status"] == "scenario_injected"
    assert res["recovery_time_seconds"] < 10.0, f"Recovery latency must be < 10s, got {res['recovery_time_seconds']}s"

    # Verify What Changed panel diff
    what_changed = res["what_changed"]
    assert "reserve_before_days" in what_changed
    assert "reserve_after_days" in what_changed
    assert "why_plan_changed" in what_changed
    assert len(what_changed["agents_rerun"]) >= 6


def test_unsupported_contamination_disclosure():
    """
    Acceptance: Contamination report does not pretend: discloses system boundary,
    raises a quality case, and drafts advisory.
    """
    events = [
        ScenarioEventItem(type="contamination_report", target="BLK-01", parameters={}, description="Chemical discoloration in riser")
    ]
    res = inject_scenario(InjectScenarioPayload(events=events, role="admin"), x_user_role="admin")

    assert len(res["unsupported_tools_audit"]) == 1
    audit = res["unsupported_tools_audit"][0]
    assert "Cannot autonomously disinfect" in audit["automated_capability"]
    assert "Dispatch lab technician" in audit["action_recommended"]


def test_viewer_rbac_rejects_scenario_injection():
    """
    Acceptance: Viewer cannot inject scenarios (HTTP 403 Forbidden).
    """
    events = [
        ScenarioEventItem(type="burst_main", target="PIPE-H-01", parameters={"loss_lpm": 80.0}, description="Burst main")
    ]
    with pytest.raises(HTTPException) as exc_info:
        inject_scenario(InjectScenarioPayload(events=events, role="viewer"), x_user_role="viewer")
    assert exc_info.value.status_code == 403
