"""
Simulated Enterprise Tools — Phase 4
Implements CMMS, SCADA (valves/pumps), Public Advisory, and Notification integrations.
Every action writes to the SQLite AuditLog and returns a rollback specification.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlmodel import Session

from ..db.database import engine, AuditLog, CMMSTicket, ApprovalItem, get_utc_now

VULNERABLE_BLOCKS = {"BLK-01", "BLK-02", "BLK-03", "BLK-04", "BLK-05", "BLK-19"}
VULNERABLE_TANKS = {"OHT-HOSTEL"}

def create_cmms_ticket(block: str, segment: str, priority: str, summary: str, actor: str = "InterventorAgent") -> Dict[str, Any]:
    """
    Simulates integration with Computerized Maintenance Management System (CMMS).
    Creates an actionable work order for field plumbing crews.
    """
    ticket_id = f"TICK-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{abs(hash(summary)) % 10000:04d}"
    with Session(engine) as session:
        ticket = CMMSTicket(
            id=ticket_id,
            tick=0,
            block_id=block,
            category="plumbing",
            priority=priority,
            status="open",
            description=f"Auto-generated ticket for {segment} at {block}: {summary}",
            cost_inr=5500.0 if priority == "urgent" else 2500.0,
            assigned_crew="Team Alpha (Hostel Utilities)" if block in VULNERABLE_BLOCKS else "Team Beta (Campus Infrastructure)"
        )
        session.add(ticket)

        audit = AuditLog(
            actor=actor,
            role="agent",
            action_type="CMMS_TICKET_CREATED",
            target_resource=segment or block,
            evidence_ids="",
            details=f"Dispatched CMMS ticket {ticket_id} [{priority}]: {summary}"
        )
        session.add(audit)
        session.commit()

    return {
        "status": "created",
        "ticket_id": ticket_id,
        "block": block,
        "segment": segment,
        "priority": priority,
        "rollback": {
            "tool": "cancel_cmms_ticket",
            "args": {"ticket_id": ticket_id},
            "description": f"Cancel CMMS maintenance ticket {ticket_id}"
        }
    }

def set_valve(valve_id: str, state: str, reason: str = "", actor: str = "InterventorAgent", target_block: Optional[str] = None) -> Dict[str, Any]:
    """
    Simulates SCADA valve actuator control (e.g., 'open', 'closed', 'throttled_50pct').
    If valve feeds a vulnerable zone, requires explicit human authorization.
    """
    is_vulnerable = (target_block in VULNERABLE_BLOCKS) or ("H-" in valve_id)
    needs_approval = is_vulnerable

    # If requires approval, register in ApprovalItem queue
    if needs_approval and actor != "admin":
        req_id = f"REQ-VALVE-{abs(hash(valve_id + state)) % 10000:04d}"
        with Session(engine) as session:
            item = ApprovalItem(
                id=req_id,
                title=f"SCADA Valve Command: Set {valve_id} to {state}",
                description=f"Interventor proposes setting {valve_id} to {state}. Reason: {reason}",
                category="zone_rationing" if state == "closed" else "pressure_modulation",
                is_vulnerable=is_vulnerable,
                equity_impact_check="CRITICAL GUARDRAIL: Valve controls supply line to residential or healthcare zone. Minimum supply must be maintained via bypass.",
                proposed_actions=f'{{"valve_id": "{valve_id}", "state": "{state}"}}',
                rollback_step=f'{{"valve_id": "{valve_id}", "state": "open"}}',
                evidence_ids="",
                status="pending"
            )
            session.add(item)
            session.commit()

        return {
            "status": "pending_approval",
            "approval_id": req_id,
            "valve_id": valve_id,
            "state": state,
            "needs_approval": True,
            "vulnerable": True,
            "rollback": {
                "tool": "set_valve",
                "args": {"valve_id": valve_id, "state": "open"},
                "description": f"Re-open valve {valve_id}"
            }
        }

    # Execute directly
    with Session(engine) as session:
        audit = AuditLog(
            actor=actor,
            role="admin" if actor == "admin" else "agent",
            action_type="SCADA_VALVE_COMMAND",
            target_resource=valve_id,
            evidence_ids="",
            details=f"Actuated valve {valve_id} -> {state}. Reason: {reason}"
        )
        session.add(audit)
        session.commit()

    return {
        "status": "executed",
        "valve_id": valve_id,
        "state": state,
        "needs_approval": False,
        "vulnerable": is_vulnerable,
        "rollback": {
            "tool": "set_valve",
            "args": {"valve_id": valve_id, "state": "open" if state == "closed" else "closed"},
            "description": f"Restore original state of valve {valve_id}"
        }
    }

def set_pump_schedule(pump_id: str, schedule: Dict[str, Any], actor: str = "InterventorAgent") -> Dict[str, Any]:
    """
    Simulates SCADA variable frequency drive (VFD) pump scheduling.
    """
    is_vulnerable = ("HOSTEL" in pump_id)
    with Session(engine) as session:
        audit = AuditLog(
            actor=actor,
            role="agent",
            action_type="PUMP_SCHEDULE_UPDATED",
            target_resource=pump_id,
            evidence_ids="",
            details=f"Updated pump schedule for {pump_id}: {schedule}"
        )
        session.add(audit)
        session.commit()

    return {
        "status": "scheduled",
        "pump_id": pump_id,
        "schedule": schedule,
        "rollback": {
            "tool": "set_pump_schedule",
            "args": {"pump_id": pump_id, "schedule": "default_diurnal"},
            "description": f"Revert pump {pump_id} to default diurnal schedule"
        }
    }

def draft_advisory(audience: str, text: str, actor: str = "InterventorAgent") -> Dict[str, Any]:
    """
    Simulates public advisory drafting for campus noticeboards, warden SMS, or email.
    """
    with Session(engine) as session:
        audit = AuditLog(
            actor=actor,
            role="agent",
            action_type="ADVISORY_DRAFTED",
            target_resource=f"audience:{audience}",
            evidence_ids="",
            details=f"Drafted advisory for {audience}: {text[:100]}..."
        )
        session.add(audit)
        session.commit()

    return {
        "status": "drafted",
        "audience": audience,
        "text": text,
        "rollback": {
            "tool": "withdraw_advisory",
            "args": {"audience": audience},
            "description": f"Withdraw advisory published to {audience}"
        }
    }

def notify(role: str, message: str, actor: str = "InterventorAgent") -> Dict[str, Any]:
    """
    Simulates direct internal notification to Estate Manager, Warden, or Maintenance Lead.
    """
    with Session(engine) as session:
        audit = AuditLog(
            actor=actor,
            role="agent",
            action_type="INTERNAL_NOTIFICATION",
            target_resource=f"role:{role}",
            evidence_ids="",
            details=f"Sent alert to {role}: {message}"
        )
        session.add(audit)
        session.commit()

    return {
        "status": "sent",
        "role": role,
        "message": message,
        "rollback": {
            "tool": "notify",
            "args": {"role": role, "message": f"DISREGARD PREVIOUS: {message}"},
            "description": "Send cancellation notice"
        }
    }
