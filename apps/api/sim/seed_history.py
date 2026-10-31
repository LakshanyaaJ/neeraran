"""
Historical Data Seeding Script (90 Simulated Days).
Generates:
- 90 days of baseline hourly readings across blocks and tanks
- 6 historical physical leak and fault events with repair dates and CMMS costs
- Initial ground_truth and audit records
"""
import random
import math
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, delete

from ..db.database import (
    engine, Reading, GroundTruth, SystemEvent, ApprovalItem, AuditLog, CMMSTicket, init_db, get_utc_now
)

def seed_90_days():
    init_db()

    with Session(engine) as session:
        # Check if already seeded
        existing_gt = session.exec(select(GroundTruth)).first()
        if existing_gt:
            print("Database already has ground truth records. Skipping re-seed.")
            return

        print("Seeding 90 days of campus water history and 6 leak repair stories...")

        rng = random.Random(42)
        base_date = datetime(2026, 5, 5, 0, 0, 0, tzinfo=timezone.utc) # 90 days before Aug 3

        # 6 Historical Ground Truth Faults & Repair Tickets
        HISTORICAL_FAULTS = [
            {
                "day_start": 14, "day_end": 16, "location": "PIPE-H-01", "type": "small_slow_leak",
                "loss_lpm": 35.0, "cost_inr": 4200.0,
                "desc": "Flange weepage on Cauvery Boys Hostel supply trunk. Gasket replaced."
            },
            {
                "day_start": 29, "day_end": 30, "location": "PIPE-H-04", "type": "small_slow_leak",
                "loss_lpm": 45.0, "cost_inr": 6500.0,
                "desc": "Corrosion weeping on Central Mess high-pressure culinary feed. Repacked valve seat."
            },
            {
                "day_start": 45, "day_end": 45, "location": "PIPE-N-02", "type": "burst_main",
                "loss_lpm": 160.0, "cost_inr": 18000.0,
                "desc": "Ground settlement burst on Science Block academic distribution. Urgent clamp sleeve applied."
            },
            {
                "day_start": 58, "day_end": 59, "location": "OHT-NORTH", "type": "tank_float_valve_failure",
                "loss_lpm": 80.0, "cost_inr": 3800.0,
                "desc": "Mechanical float stuck open on North Academic OHT. Overflowed to storm drain; valve replaced."
            },
            {
                "day_start": 71, "day_end": 75, "location": "BLK-11", "type": "meter_fault",
                "loss_lpm": 0.0, "cost_inr": 8500.0,
                "desc": "Ultrasonic flow meter transducer failure at Nanotech Lab. Read flat zero for 4 days; recalibrated."
            },
            {
                "day_start": 83, "day_end": 85, "location": "PIPE-H-03", "type": "small_slow_leak",
                "loss_lpm": 50.0, "cost_inr": 5400.0,
                "desc": "Sub-surface joint leak on Vaigai Girls Hostel line. Excavated and collar-welded."
            },
        ]

        # Insert Ground Truth and CMMS Tickets
        for i, hf in enumerate(HISTORICAL_FAULTS):
            start_tick = hf["day_start"] * 288
            end_tick = hf["day_end"] * 288
            f_id = f"GT-HIST-0{i+1}"

            gt = GroundTruth(
                fault_id=f_id,
                fault_type=hf["type"],
                entity_id=hf["location"],
                start_tick=start_tick,
                end_tick=end_tick,
                true_loss_rate_lpm=hf["loss_lpm"],
                details=hf["desc"],
                is_active=False # already resolved
            )
            session.add(gt)

            ticket = CMMSTicket(
                id=f"CMMS-TICK-2026-0{i+1}",
                tick=end_tick,
                block_id=hf["location"],
                category="plumbing" if "leak" in hf["type"] or "burst" in hf["type"] else "meter",
                priority="urgent" if "burst" in hf["type"] else "medium",
                status="closed",
                description=hf["desc"],
                assigned_crew="Campus Plumbing Quick-Response Unit A",
                created_at=base_date + timedelta(days=hf["day_start"]),
                resolved_at=base_date + timedelta(days=hf["day_end"]),
                cost_inr=hf["cost_inr"]
            )
            session.add(ticket)

            # Audit log
            audit = AuditLog(
                actor="Chief Estate Engineer",
                role="admin",
                action_type="CLOSE_WORK_ORDER",
                target_resource=hf["location"],
                evidence_ids=f"EVID-HIST-{i+1}",
                details=f"Work order closed for {hf['desc']}. Total repair cost: INR {hf['cost_inr']}",
                status="success"
            )
            session.add(audit)

        # Seed rolling window readings (Sampled every 3 hours for 90 days to keep database fast & under 5MB)
        entities = [
            ("BLK-01", "block_flow", 79.7, "L/min"),
            ("BLK-02", "block_flow", 70.3, "L/min"),
            ("BLK-03", "block_flow", 84.4, "L/min"),
            ("BLK-04", "block_flow", 17.4, "L/min"),
            ("BLK-06", "block_flow", 104.2, "L/min"),
            ("BLK-07", "block_flow", 56.3, "L/min"),
            ("PIPE-H-01", "pipe_pressure", 2.45, "bar"),
            ("PIPE-H-03", "pipe_pressure", 2.40, "bar"),
            ("OHT-HOSTEL", "tank_level", 4.10, "m"),
            ("SUMP-MAIN", "tank_level", 4.65, "m"),
        ]

        readings_to_add = []
        for day in range(90):
            for hour in range(0, 24, 3):
                t_offset = day * 288 + (hour * 12)
                sim_t = base_date + timedelta(days=day, hours=hour)
                is_weekend = sim_t.weekday() >= 5

                for ent_id, metric, base_val, unit in entities:
                    val = base_val
                    if metric == "block_flow":
                        if 5 <= hour <= 8:
                            mult = 2.1
                        elif 12 <= hour <= 14:
                            mult = 2.4 if ent_id == "BLK-06" else 1.3
                        elif 18 <= hour <= 21:
                            mult = 1.9
                        elif 0 <= hour <= 4:
                            mult = 0.15 # Night minimum
                        else:
                            mult = 0.6
                        val = base_val * mult * rng.uniform(0.95, 1.05)

                    elif metric == "pipe_pressure":
                        val = base_val + rng.uniform(-0.05, 0.05)

                    elif metric == "tank_level":
                        val = min(5.0, max(1.5, base_val + 0.6 * math.sin(hour / 4.0) + rng.uniform(-0.1, 0.1)))

                    readings_to_add.append(
                        Reading(
                            tick=t_offset,
                            sim_time=sim_t,
                            metric_type=metric,
                            entity_id=ent_id,
                            value=round(val, 2),
                            unit=unit,
                            quality="good"
                        )
                    )

        session.add_all(readings_to_add)
        session.commit()
        print(f"Successfully seeded {len(readings_to_add)} historical telemetry readings and 6 leak stories!")

if __name__ == "__main__":
    seed_90_days()
