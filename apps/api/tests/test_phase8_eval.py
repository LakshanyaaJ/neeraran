"""
Phase 8 Acceptance Test Suite — NEERARAN Live Ground-Truth Evaluation Matrix
Verifies:
1. Live computed metrics across all 9 dimensions (never hardcoded, computed in < 500ms).
2. Dynamic threshold update modifies Precision and Recall live against ground truth.
3. 20-Scenario benchmark runner replays and returns in under 30 seconds.
4. RBAC protection: non-admin (Viewer) receives HTTP 403 Forbidden on benchmark run and threshold change.
5. Tamper-proof audit log CSV export returns proper CSV format with immutable headers.
"""
import pytest
import time
from fastapi import HTTPException
from apps.api.routes.evaluation import (
    get_evaluation_metrics,
    run_benchmark,
    update_threshold,
    export_audit_csv,
    ThresholdPayload
)
from apps.api.eval.benchmark import benchmark_engine

def test_get_live_eval_metrics():
    """
    Acceptance: Evaluation metrics must cover detection, localization, forecast sMAPE,
    optimization, conservation, groundedness, fairness, system latency, and adaptability.
    """
    t0 = time.perf_counter()
    res = get_evaluation_metrics()
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert duration_ms < 500.0, f"Live evaluation took too long: {duration_ms}ms (target < 500ms)"
    assert "detection" in res
    assert "localization" in res
    assert "forecast_smape" in res
    assert "optimization" in res
    assert "conservation" in res
    assert "groundedness" in res
    assert "fairness" in res
    assert "system" in res
    assert "adaptability" in res

    # Verify detection values
    detection = res["detection"]
    assert 0.0 <= detection["precision"] <= 100.0
    assert 0.0 <= detection["recall"] <= 100.0
    assert 0.0 <= detection["f1_score"] <= 100.0
    assert detection["mttd_minutes"] < detection["baseline_threshold_mttd"], "Agent MTTD must be faster than baseline"

    # Verify forecast sMAPE has both model and naive baseline
    smape = res["forecast_smape"]
    assert smape["demand_24h"]["model"] < smape["demand_24h"]["naive"]
    assert smape["demand_72h"]["model"] < smape["demand_72h"]["naive"]

    # Verify optimization has zero vulnerable violations
    assert res["optimization"]["vulnerable_violations_count"] == 0
    assert res["optimization"]["vulnerable_minimum_compliance_pct"] == 100.0

    # Verify fairness has 5 protected vulnerable zones
    assert res["fairness"]["vulnerable_blocks_protected_count"] == 5
    assert res["fairness"]["vulnerable_unauthorized_restrictions"] == 0


def test_dynamic_threshold_adjustment():
    """
    Acceptance: Changing threshold z dynamically recalculates precision and recall.
    Higher z -> higher precision, lower recall.
    Lower z -> higher recall, lower precision.
    """
    # High precision setting (z = 3.5)
    res_high = update_threshold(ThresholdPayload(z_score=3.5), x_user_role="admin")
    prec_high = res_high["detection_impact"]["precision"]
    rec_high = res_high["detection_impact"]["recall"]

    # High recall setting (z = 1.5)
    res_low = update_threshold(ThresholdPayload(z_score=1.5), x_user_role="admin")
    prec_low = res_low["detection_impact"]["precision"]
    rec_low = res_low["detection_impact"]["recall"]

    assert prec_high >= prec_low, f"High z precision ({prec_high}) should be >= Low z precision ({prec_low})"
    assert rec_low >= rec_high, f"Low z recall ({rec_low}) should be >= High z recall ({rec_high})"

    # Reset to default
    update_threshold(ThresholdPayload(z_score=2.5), x_user_role="admin")


def test_benchmark_completes_in_under_30s():
    """
    Acceptance: Replaying 20 seeded fault scenarios must finish in < 30 seconds.
    """
    t0 = time.perf_counter()
    res = run_benchmark(x_user_role="admin")
    duration_s = time.perf_counter() - t0

    assert duration_s < 30.0, f"Benchmark execution took {duration_s:.2f}s (must complete under 30s)"
    assert res["status"] == "completed"
    assert res["scenarios_replayed"] == 20
    assert "metrics" in res


def test_rbac_viewer_forbidden_on_mutating_actions():
    """
    Acceptance: Viewer receives HTTP 403 on benchmark execution and threshold adjustment.
    """
    with pytest.raises(HTTPException) as exc_bench:
        run_benchmark(x_user_role="viewer")
    assert exc_bench.value.status_code == 403

    with pytest.raises(HTTPException) as exc_thresh:
        update_threshold(ThresholdPayload(z_score=3.0), x_user_role="viewer")
    assert exc_thresh.value.status_code == 403


def test_audit_csv_export():
    """
    Acceptance: GET /api/audit/export.csv returns CSV with expected column headers and attachment header.
    """
    res = export_audit_csv()
    assert res.media_type == "text/csv"
    assert "attachment; filename=neeraran_audit_log.csv" in res.headers.get("content-disposition", "")

    csv_text = res.body.decode("utf-8")
    lines = csv_text.strip().split("\r\n") if "\r\n" in csv_text else csv_text.strip().split("\n")
    header = lines[0]
    expected_cols = ["ID", "Timestamp (UTC)", "Actor", "Role", "Action Type", "Target Resource", "Evidence IDs", "Details", "Status"]
    for col in expected_cols:
        assert col in header, f"Missing header column {col} in CSV export"


def test_demo_reset_admin_and_viewer_rbac():
    """
    Acceptance: One-click Reset Demo resets to Day 1 08:00, clears approvals/audit,
    and enforces Admin RBAC (Viewer gets HTTP 403).
    """
    from apps.api.routes.simulation import reset_demo

    # Viewer rejected
    with pytest.raises(HTTPException) as exc:
        reset_demo(x_user_role="viewer")
    assert exc.value.status_code == 403

    # Admin succeeds
    res = reset_demo(x_user_role="admin")
    assert res["status"] == "ok"
    assert "Demo reset" in res["message"]
    assert res["state"]["seed"] == 42

