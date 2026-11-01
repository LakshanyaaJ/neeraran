"""
Evaluation & Responsible AI Router — Phase 8
Exposes live quantitative benchmark metrics, 20-scenario replay benchmark,
adjustable threshold testing, and immutable CSV audit export.
"""
import io
import csv
from fastapi import APIRouter, HTTPException, Header, Body, Response
from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlmodel import Session, select, desc

from ..eval.benchmark import benchmark_engine
from ..db.database import engine, AuditLog, ApprovalItem

router = APIRouter(tags=["evaluation"])

class ThresholdPayload(BaseModel):
    z_score: float

@router.get("/api/eval/metrics")
def get_evaluation_metrics():
    """Retrieve computed evaluation metrics across all 9 dimensions."""
    if benchmark_engine.cached_benchmark:
        return benchmark_engine.cached_benchmark["metrics"]
    return benchmark_engine.compute_live_metrics()

@router.post("/api/eval/benchmark")
def run_benchmark(x_user_role: Optional[str] = Header(None)):
    """
    Executes full 20-scenario ground-truth benchmark suite.
    ADMIN ONLY: Returns in < 30 seconds.
    """
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only Estate Admin can execute the benchmark runner.")

    result = benchmark_engine.run_full_benchmark(scenarios_count=20)
    return result

@router.post("/api/eval/threshold")
def update_threshold(payload: ThresholdPayload, x_user_role: Optional[str] = Header(None)):
    """
    Updates the leak detection z-score threshold and re-evaluates precision & recall live.
    ADMIN ONLY.
    """
    if x_user_role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Only Estate Admin can update evaluation thresholds.")

    benchmark_engine.set_leak_threshold(payload.z_score)
    metrics = benchmark_engine.compute_live_metrics()
    return {
        "status": "ok",
        "new_threshold_z": payload.z_score,
        "detection_impact": metrics["detection"]
    }

@router.get("/api/audit/export.csv")
def export_audit_csv():
    """
    Downloads the entire immutable system audit trail as a standard CSV file.
    """
    with Session(engine) as session:
        logs = session.exec(select(AuditLog).order_by(desc(AuditLog.id))).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp (UTC)", "Actor", "Role", "Action Type", "Target Resource", "Evidence IDs", "Details", "Status"])

    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat() if log.timestamp else "",
            log.actor,
            log.role,
            log.action_type,
            log.target_resource,
            log.evidence_ids or "",
            log.details,
            log.status
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=neeraran_audit_log.csv"}
    )

