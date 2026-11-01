"""
Campus GeoJSON API Endpoints — Phase 3
"""
from fastapi import APIRouter
from typing import Dict, Any
import json
import os

router = APIRouter(prefix="/api/campus", tags=["campus"])

GEOJSON_PATH = "apps/api/data/campus.geojson"

@router.get("")
@router.get("/")
@router.get("/topology")
def get_campus_geojson() -> Dict[str, Any]:
    """Returns the full GeoJSON digital twin model of the campus."""
    if os.path.exists(GEOJSON_PATH):
        with open(GEOJSON_PATH, "r") as f:
            return json.load(f)
    return {"type": "FeatureCollection", "features": []}
