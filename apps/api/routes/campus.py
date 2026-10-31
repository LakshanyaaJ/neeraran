"""
Campus topology endpoints for digital twin visualization.
"""
from fastapi import APIRouter
from typing import Dict, Any, List
from ..sim.campus_model import (
    BLOCKS_DATA, TANKS_DATA, BOREWELLS_DATA, SUMP_DATA, STP_DATA,
    PIPE_SEGMENTS_DATA, CAMPUS_CENTER
)
from ..sim.engine import simulator_instance

router = APIRouter(prefix="/api/campus", tags=["campus"])

@router.get("/topology")
def get_campus_topology() -> Dict[str, Any]:
    """
    Returns full GeoJSON and structural graph of the 20-block campus twin.
    """
    geojson_features = []

    # 1. Blocks as Points / Polygons
    for blk in BLOCKS_DATA:
        geojson_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": blk["coordinates"]
            },
            "properties": {
                "id": blk["id"],
                "name": blk["name"],
                "code": blk["code"],
                "asset_type": "block",
                "category": blk["category"],
                "population": blk["population"],
                "is_vulnerable": blk["is_vulnerable"],
                "fed_by": blk["fed_by_tank_id"],
                "baseline_demand_lpm": blk["baseline_demand_lpm"]
            }
        })

    # 2. Tanks
    for t in TANKS_DATA:
        geojson_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": t["coordinates"]
            },
            "properties": {
                "id": t["id"],
                "name": t["name"],
                "asset_type": "tank",
                "capacity_kl": t["capacity_kl"],
                "serves_blocks": t["serves_blocks"]
            }
        })

    # 3. Borewells
    for b in BOREWELLS_DATA:
        geojson_features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": b["coordinates"]
            },
            "properties": {
                "id": b["id"],
                "name": b["name"],
                "asset_type": "borewell",
                "depth_m": b["depth_m"],
                "max_yield_lpm": b["max_yield_lpm"]
            }
        })

    # 4. Sump
    geojson_features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": SUMP_DATA["coordinates"]
        },
        "properties": {
            "id": SUMP_DATA["id"],
            "name": SUMP_DATA["name"],
            "asset_type": "sump",
            "capacity_kl": SUMP_DATA["capacity_kl"]
        }
    })

    # 5. STP
    geojson_features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": STP_DATA["coordinates"]
        },
        "properties": {
            "id": STP_DATA["id"],
            "name": STP_DATA["name"],
            "asset_type": "stp",
            "capacity_kld": STP_DATA["capacity_kld"]
        }
    })

    # 6. Pipe Segments as LineStrings
    for p in PIPE_SEGMENTS_DATA:
        geojson_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": p["coordinates"]
            },
            "properties": {
                "id": p["id"],
                "from_node": p["from_node"],
                "to_node": p["to_node"],
                "asset_type": "pipe",
                "diameter_mm": p["diameter_mm"],
                "length_m": p["length_m"]
            }
        })

    return {
        "campus_center": CAMPUS_CENTER,
        "geojson": {
            "type": "FeatureCollection",
            "features": geojson_features
        },
        "summary": {
            "blocks_count": len(BLOCKS_DATA),
            "tanks_count": len(TANKS_DATA),
            "borewells_count": len(BOREWELLS_DATA),
            "sump_capacity_kl": SUMP_DATA["capacity_kl"],
            "stp_capacity_kld": STP_DATA["capacity_kld"],
            "pipe_segments_count": len(PIPE_SEGMENTS_DATA)
        }
    }

