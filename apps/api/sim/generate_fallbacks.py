"""
Generate static JSON fallback snapshots for NEERARAN:
- campus.json: Full campus GeoJSON and topology index
- day_snapshot.json: 288 ticks (24 hours) of normal deterministic simulation
- leak_story.json: 48 hours containing a ground-truth burst event on PIPE-H-03 with physical response
"""
import json
import os
import shutil
from datetime import datetime, timezone
from apps.api.sim.engine import CampusSimulatorPhase3

def generate_fallbacks():
    print("Generating campus.json...")
    with open("apps/api/data/campus.geojson", "r") as f:
        campus_data = json.load(f)

    # 1. Save campus.json
    for out_dir in ["public/fallback", "apps/web/public/fallback"]:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "campus.json"), "w") as f:
            json.dump(campus_data, f, indent=2)

    # 2. Generate day_snapshot.json (288 ticks = 1 full day of normal telemetry)
    print("Generating day_snapshot.json (288 ticks)...")
    sim = CampusSimulatorPhase3(seed=42)
    day_ticks = []
    
    for t in range(288):
        sim.tick(1)
        st = sim.get_state()
        # Compress tick entry for crisp frontend consumption
        tick_summary = {
            "tick": st["tick"],
            "sim_time": st["sim_time"],
            "hour_of_day": st["hour_of_day"],
            "total_demand_lpm": round(sum(b["current_lpm"] for b in st["blocks"]), 1),
            "total_storage_kl": round(st["sump"]["current_kl"] + sum(t["current_kl"] for t in st["tanks"]), 1),
            "sump": {
                "level_m": st["sump"]["level_m"],
                "current_kl": st["sump"]["current_kl"],
                "pct_full": st["sump"]["pct_full"]
            },
            "tanks": {
                t["id"]: {
                    "level_m": t["level_m"],
                    "current_kl": t["current_kl"],
                    "pct_full": t["pct_full"]
                }
                for t in st["tanks"]
            },
            "blocks": {
                b["id"]: {
                    "meter_reading_lpm": b["meter_reading_lpm"],
                    "pressure_bar": b["pressure_bar"],
                    "vulnerable": b["vulnerable"]
                }
                for b in st["blocks"]
            },
            "pipes": {
                p["id"]: {
                    "flow_lpm": p["flow_lpm"],
                    "pressure_bar": p["pressure_bar"],
                    "has_fault": p["has_fault"]
                }
                for p in st["pipes"]
            },
            "weather": {
                "temp_c": st["weather"]["temp_c"],
                "rainfall_mm": st["weather"]["rainfall_mm"]
            }
        }
        day_ticks.append(tick_summary)

    day_payload = {
        "metadata": {
            "description": "24-hour diurnal baseline of campus water digital twin (288 ticks at 5-min intervals)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_ticks": 288,
            "seed": 42
        },
        "ticks": day_ticks,
        "final_state": sim.get_state()
    }

    for out_dir in ["public/fallback", "apps/web/public/fallback"]:
        with open(os.path.join(out_dir, "day_snapshot.json"), "w") as f:
            json.dump(day_payload, f, indent=2)

    # 3. Generate leak_story.json (A 48-hour story with an injected burst)
    print("Generating leak_story.json (burst event on PIPE-H-03)...")
    sim_leak = CampusSimulatorPhase3(seed=42)
    leak_story_ticks = []
    
    # Run 120 ticks (10 hours) normally
    for _ in range(120):
        sim_leak.tick(1)
        leak_story_ticks.append({
            "tick": sim_leak.current_tick,
            "sim_time": sim_leak.get_sim_time().isoformat(),
            "status": "normal",
            "cauvery_meter_lpm": sim_leak.blocks["BLK-01"]["meter_reading_lpm"],
            "cauvery_pressure_bar": sim_leak.blocks["BLK-01"]["pressure_bar"],
            "oht_hostel_level_m": sim_leak.tanks["OHT-HOSTEL"]["current_level_m"],
            "pipe_h03_loss_lpm": sim_leak.pipes["PIPE-H-03"]["true_leak_lpm"]
        })

    # At tick 121, inject pipe burst on PIPE-H-03 (feeds Cauvery Hostel BLK-01)
    burst_fault = sim_leak.inject_fault(
        fault_type="burst_main",
        entity_id="PIPE-H-03",
        true_loss_rate_lpm=85.0,
        details="Ground rupture on main supply line to Cauvery Hostel"
    )

    # Run for 72 ticks under active leak (6 hours of burst)
    for _ in range(72):
        sim_leak.tick(1)
        leak_story_ticks.append({
            "tick": sim_leak.current_tick,
            "sim_time": sim_leak.get_sim_time().isoformat(),
            "status": "leak_active",
            "cauvery_meter_lpm": sim_leak.blocks["BLK-01"]["meter_reading_lpm"],
            "cauvery_pressure_bar": sim_leak.blocks["BLK-01"]["pressure_bar"],
            "oht_hostel_level_m": sim_leak.tanks["OHT-HOSTEL"]["current_level_m"],
            "pipe_h03_loss_lpm": sim_leak.pipes["PIPE-H-03"]["true_leak_lpm"]
        })

    # At tick 193, repair/isolate the pipe
    sim_leak.pipes["PIPE-H-03"]["true_leak_lpm"] = 0.0
    sim_leak.pipes["PIPE-H-03"]["has_fault"] = False
    if burst_fault["fault_id"] in sim_leak.active_faults:
        sim_leak.active_faults[burst_fault["fault_id"]]["is_active"] = False

    # Run for another 48 ticks post-repair
    for _ in range(48):
        sim_leak.tick(1)
        leak_story_ticks.append({
            "tick": sim_leak.current_tick,
            "sim_time": sim_leak.get_sim_time().isoformat(),
            "status": "resolved",
            "cauvery_meter_lpm": sim_leak.blocks["BLK-01"]["meter_reading_lpm"],
            "cauvery_pressure_bar": sim_leak.blocks["BLK-01"]["pressure_bar"],
            "oht_hostel_level_m": sim_leak.tanks["OHT-HOSTEL"]["current_level_m"],
            "pipe_h03_loss_lpm": sim_leak.pipes["PIPE-H-03"]["true_leak_lpm"]
        })

    leak_story_payload = {
        "metadata": {
            "title": "Ground Truth Event: Main Pipe Rupture on Cauvery Hostel Supply Line",
            "entity_id": "PIPE-H-03",
            "fault_type": "burst_main",
            "true_loss_rate_lpm": 85.0,
            "start_tick": 121,
            "isolated_tick": 193,
            "total_water_lost_litres": round(85.0 * (193 - 121) * 5, 0),
            "evidence_chain": [
                {"tick": 121, "type": "FAULT_ONSET", "desc": "Pipe shear on 150mm DI line"},
                {"tick": 125, "type": "TELEMETRY_DROP", "desc": "BLK-01 pressure dropped from 2.45 to 1.38 bar"},
                {"tick": 136, "type": "STORAGE_ACCEL", "desc": "OHT-01 drawdown velocity increased +140%"},
                {"tick": 142, "type": "COMPLAINT_FILED", "desc": "Warden reports low shower pressure on 3rd floor"},
                {"tick": 193, "type": "VALVE_ISOLATION", "desc": "Emergency bypass valve V-03 engaged"}
            ]
        },
        "timeline": leak_story_ticks
    }

    for out_dir in ["public/fallback", "apps/web/public/fallback"]:
        with open(os.path.join(out_dir, "leak_story.json"), "w") as f:
            json.dump(leak_story_payload, f, indent=2)

    print("All fallback snapshots successfully written to public/fallback and apps/web/public/fallback!")

if __name__ == "__main__":
    generate_fallbacks()
