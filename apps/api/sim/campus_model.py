"""
Synthetic Campus Digital Twin Topology Model.
Defines all 20 campus blocks, 4 overhead tanks, 2 borewells, 1 sump, 1 STP,
and the hydraulic pipe segment network.
"""
from typing import List, Dict, Any

# Campus anchor point (Latitude, Longitude in Tamil Nadu, India)
CAMPUS_CENTER = [80.2220, 12.9870] # [lng, lat]

BLOCKS_DATA: List[Dict[str, Any]] = [
    {
        "id": "BLK-01",
        "name": "Cauvery Boys Hostel",
        "code": "CBH",
        "category": "residential",
        "population": 850,
        "is_vulnerable": True,
        "fed_by_tank_id": "OHT-HOSTEL",
        "coordinates": [80.2185, 12.9892],
        "baseline_demand_lpm": 95.0, # ~135 L/person/day
    },
    {
        "id": "BLK-02",
        "name": "Krishna Boys Hostel",
        "code": "KBH",
        "category": "residential",
        "population": 750,
        "is_vulnerable": True,
        "fed_by_tank_id": "OHT-HOSTEL",
        "coordinates": [80.2198, 12.9901],
        "baseline_demand_lpm": 84.0,
    },
    {
        "id": "BLK-03",
        "name": "Vaigai Girls Hostel",
        "code": "VGH",
        "category": "residential",
        "population": 900,
        "is_vulnerable": True,
        "fed_by_tank_id": "OHT-HOSTEL",
        "coordinates": [80.2172, 12.9880],
        "baseline_demand_lpm": 100.0,
    },
    {
        "id": "BLK-04",
        "name": "Campus Health Centre",
        "code": "HLC",
        "category": "health",
        "population": 35,
        "is_vulnerable": True, # Strict vulnerable: dialysis/sterilization/inpatient
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2235, 12.9875],
        "baseline_demand_lpm": 22.0,
    },
    {
        "id": "BLK-05",
        "name": "Campus Daycare & Crèche",
        "code": "CRC",
        "category": "health",
        "population": 45,
        "is_vulnerable": True, # Strict vulnerable: infant care
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2241, 12.9868],
        "baseline_demand_lpm": 16.0,
    },
    {
        "id": "BLK-06",
        "name": "Central Mess & Dining Complex",
        "code": "MES",
        "category": "utility",
        "population": 2500,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-HOSTEL",
        "coordinates": [80.2205, 12.9885],
        "baseline_demand_lpm": 120.0, # High culinary washing/steam boiling
    },
    {
        "id": "BLK-07",
        "name": "Ramanujan Hall (Academic Block A)",
        "code": "ACA",
        "category": "academic",
        "population": 1800,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-NORTH",
        "coordinates": [80.2225, 12.9915],
        "baseline_demand_lpm": 65.0,
    },
    {
        "id": "BLK-08",
        "name": "Sir C.V. Raman Science Block (Academic Block B)",
        "code": "ACB",
        "category": "academic",
        "population": 1400,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-NORTH",
        "coordinates": [80.2240, 12.9922],
        "baseline_demand_lpm": 72.0,
    },
    {
        "id": "BLK-09",
        "name": "Alan Turing Computing Complex (Academic Block C)",
        "code": "ACC",
        "category": "academic",
        "population": 1600,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-NORTH",
        "coordinates": [80.2255, 12.9910],
        "baseline_demand_lpm": 55.0,
    },
    {
        "id": "BLK-10",
        "name": "Central Library & Knowledge Resource Centre",
        "code": "LIB",
        "category": "academic",
        "population": 600,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2215, 12.9870],
        "baseline_demand_lpm": 28.0,
    },
    {
        "id": "BLK-11",
        "name": "Nanotech & Biotech Research Facility",
        "code": "LAB",
        "category": "academic",
        "population": 250,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-SOUTH",
        "coordinates": [80.2260, 12.9880],
        "baseline_demand_lpm": 50.0, # Pure water deionization loops
    },
    {
        "id": "BLK-12",
        "name": "Aquatics & Sports Complex",
        "code": "SPT",
        "category": "sports",
        "population": 400,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-SOUTH",
        "coordinates": [80.2272, 12.9845],
        "baseline_demand_lpm": 60.0,
    },
    {
        "id": "BLK-13",
        "name": "Administrative Bhavan",
        "code": "ADM",
        "category": "admin",
        "population": 300,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2210, 12.9855],
        "baseline_demand_lpm": 25.0,
    },
    {
        "id": "BLK-14",
        "name": "Executive Campus Guest House",
        "code": "GHS",
        "category": "residential",
        "population": 60,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2230, 12.9842],
        "baseline_demand_lpm": 20.0,
    },
    {
        "id": "BLK-15",
        "name": "Student Activity Centre (SAC)",
        "code": "SAC",
        "category": "sports",
        "population": 500,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-SOUTH",
        "coordinates": [80.2250, 12.9852],
        "baseline_demand_lpm": 35.0,
    },
    {
        "id": "BLK-16",
        "name": "Workshop & Fabrication Hub",
        "code": "WKS",
        "category": "academic",
        "population": 220,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-NORTH",
        "coordinates": [80.2270, 12.9902],
        "baseline_demand_lpm": 28.0,
    },
    {
        "id": "BLK-17",
        "name": "Electrical Substation & Utility Annex",
        "code": "UTL",
        "category": "utility",
        "population": 50,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-SOUTH",
        "coordinates": [80.2280, 12.9868],
        "baseline_demand_lpm": 12.0,
    },
    {
        "id": "BLK-18",
        "name": "Main Gatehouse & Security Hub",
        "code": "SEC",
        "category": "admin",
        "population": 30,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2165, 12.9840],
        "baseline_demand_lpm": 8.0,
    },
    {
        "id": "BLK-19",
        "name": "Campus Cafeteria & Kiosk Plaza",
        "code": "CAF",
        "category": "utility",
        "population": 350,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-HOSTEL",
        "coordinates": [80.2190, 12.9865],
        "baseline_demand_lpm": 30.0,
    },
    {
        "id": "BLK-20",
        "name": "Faculty Housing Enclave",
        "code": "FAC",
        "category": "residential",
        "population": 400,
        "is_vulnerable": False,
        "fed_by_tank_id": "OHT-ADMIN",
        "coordinates": [80.2250, 12.9830],
        "baseline_demand_lpm": 48.0,
    },
]

TANKS_DATA: List[Dict[str, Any]] = [
    {
        "id": "OHT-HOSTEL",
        "name": "Overhead Tank Hostels & Dining",
        "capacity_kl": 100.0,
        "initial_level_kl": 82.0,
        "fed_by_pump": "PUMP-01",
        "coordinates": [80.2195, 12.9888],
        "serves_blocks": ["BLK-01", "BLK-02", "BLK-03", "BLK-06", "BLK-19"]
    },
    {
        "id": "OHT-NORTH",
        "name": "Overhead Tank North Academic",
        "capacity_kl": 80.0,
        "initial_level_kl": 64.0,
        "fed_by_pump": "PUMP-02",
        "coordinates": [80.2238, 12.9918],
        "serves_blocks": ["BLK-07", "BLK-08", "BLK-09", "BLK-16"]
    },
    {
        "id": "OHT-SOUTH",
        "name": "Overhead Tank South Labs & Sports",
        "capacity_kl": 80.0,
        "initial_level_kl": 61.5,
        "fed_by_pump": "PUMP-03",
        "coordinates": [80.2265, 12.9865],
        "serves_blocks": ["BLK-11", "BLK-12", "BLK-15", "BLK-17"]
    },
    {
        "id": "OHT-ADMIN",
        "name": "Overhead Tank Admin & Health Enclave",
        "capacity_kl": 60.0,
        "initial_level_kl": 49.0,
        "fed_by_pump": "PUMP-04",
        "coordinates": [80.2225, 12.9858],
        "serves_blocks": ["BLK-04", "BLK-05", "BLK-10", "BLK-13", "BLK-14", "BLK-18", "BLK-20"]
    }
]

BOREWELLS_DATA: List[Dict[str, Any]] = [
    {
        "id": "BW-01",
        "name": "Deep Borewell 1 (North Aquifer)",
        "depth_m": 180.0,
        "max_yield_lpm": 250.0,
        "power_kw": 18.5,
        "coordinates": [80.2200, 12.9930]
    },
    {
        "id": "BW-02",
        "name": "Deep Borewell 2 (South Aquifer)",
        "depth_m": 210.0,
        "max_yield_lpm": 200.0,
        "power_kw": 15.0,
        "coordinates": [80.2285, 12.9835]
    }
]

SUMP_DATA: Dict[str, Any] = {
    "id": "SUMP-MAIN",
    "name": "Central Campus Raw Water Sump",
    "capacity_kl": 500.0,
    "initial_level_kl": 390.0,
    "coordinates": [80.2215, 12.9880]
}

STP_DATA: Dict[str, Any] = {
    "id": "STP-MAIN",
    "name": "Sewage Treatment & Greywater Reclamation Facility",
    "capacity_kld": 150.0,
    "coordinates": [80.2290, 12.9890]
}

# 24 Hydraulic Pipe Segments with GeoJSON Line Coordinates
PIPE_SEGMENTS_DATA: List[Dict[str, Any]] = [
    # Borewell to Sump raw supply mains
    {"id": "PIPE-BW1", "from_node": "BW-01", "to_node": "SUMP-MAIN", "diameter_mm": 150, "length_m": 580.0,
     "coordinates": [[80.2200, 12.9930], [80.2215, 12.9880]]},
    {"id": "PIPE-BW2", "from_node": "BW-02", "to_node": "SUMP-MAIN", "diameter_mm": 150, "length_m": 920.0,
     "coordinates": [[80.2285, 12.9835], [80.2215, 12.9880]]},

    # Sump to OHT Pumping Risers
    {"id": "PIPE-P1-OHTH", "from_node": "SUMP-MAIN", "to_node": "OHT-HOSTEL", "diameter_mm": 200, "length_m": 240.0,
     "coordinates": [[80.2215, 12.9880], [80.2195, 12.9888]]},
    {"id": "PIPE-P2-OHTN", "from_node": "SUMP-MAIN", "to_node": "OHT-NORTH", "diameter_mm": 150, "length_m": 480.0,
     "coordinates": [[80.2215, 12.9880], [80.2238, 12.9918]]},
    {"id": "PIPE-P3-OHTS", "from_node": "SUMP-MAIN", "to_node": "OHT-SOUTH", "diameter_mm": 150, "length_m": 570.0,
     "coordinates": [[80.2215, 12.9880], [80.2265, 12.9865]]},
    {"id": "PIPE-P4-OHTA", "from_node": "SUMP-MAIN", "to_node": "OHT-ADMIN", "diameter_mm": 125, "length_m": 260.0,
     "coordinates": [[80.2215, 12.9880], [80.2225, 12.9858]]},

    # OHT-Hostel Gravity Distribution Mains
    {"id": "PIPE-H-01", "from_node": "OHT-HOSTEL", "to_node": "BLK-01", "diameter_mm": 100, "length_m": 120.0,
     "coordinates": [[80.2195, 12.9888], [80.2185, 12.9892]]},
    {"id": "PIPE-H-02", "from_node": "OHT-HOSTEL", "to_node": "BLK-02", "diameter_mm": 100, "length_m": 150.0,
     "coordinates": [[80.2195, 12.9888], [80.2198, 12.9901]]},
    {"id": "PIPE-H-03", "from_node": "OHT-HOSTEL", "to_node": "BLK-03", "diameter_mm": 100, "length_m": 270.0,
     "coordinates": [[80.2195, 12.9888], [80.2172, 12.9880]]},
    {"id": "PIPE-H-04", "from_node": "OHT-HOSTEL", "to_node": "BLK-06", "diameter_mm": 125, "length_m": 115.0,
     "coordinates": [[80.2195, 12.9888], [80.2205, 12.9885]]},
    {"id": "PIPE-H-05", "from_node": "OHT-HOSTEL", "to_node": "BLK-19", "diameter_mm": 75, "length_m": 260.0,
     "coordinates": [[80.2195, 12.9888], [80.2190, 12.9865]]},

    # OHT-North Academic Gravity Mains
    {"id": "PIPE-N-01", "from_node": "OHT-NORTH", "to_node": "BLK-07", "diameter_mm": 100, "length_m": 150.0,
     "coordinates": [[80.2238, 12.9918], [80.2225, 12.9915]]},
    {"id": "PIPE-N-02", "from_node": "OHT-NORTH", "to_node": "BLK-08", "diameter_mm": 100, "length_m": 60.0,
     "coordinates": [[80.2238, 12.9918], [80.2240, 12.9922]]},
    {"id": "PIPE-N-03", "from_node": "OHT-NORTH", "to_node": "BLK-09", "diameter_mm": 100, "length_m": 210.0,
     "coordinates": [[80.2238, 12.9918], [80.2255, 12.9910]]},
    {"id": "PIPE-N-04", "from_node": "OHT-NORTH", "to_node": "BLK-16", "diameter_mm": 75, "length_m": 380.0,
     "coordinates": [[80.2238, 12.9918], [80.2270, 12.9902]]},

    # OHT-South Labs & Sports Gravity Mains
    {"id": "PIPE-S-01", "from_node": "OHT-SOUTH", "to_node": "BLK-11", "diameter_mm": 100, "length_m": 175.0,
     "coordinates": [[80.2265, 12.9865], [80.2260, 12.9880]]},
    {"id": "PIPE-S-02", "from_node": "OHT-SOUTH", "to_node": "BLK-12", "diameter_mm": 100, "length_m": 235.0,
     "coordinates": [[80.2265, 12.9865], [80.2272, 12.9845]]},
    {"id": "PIPE-S-03", "from_node": "OHT-SOUTH", "to_node": "BLK-15", "diameter_mm": 75, "length_m": 210.0,
     "coordinates": [[80.2265, 12.9865], [80.2250, 12.9852]]},
    {"id": "PIPE-S-04", "from_node": "OHT-SOUTH", "to_node": "BLK-17", "diameter_mm": 50, "length_m": 165.0,
     "coordinates": [[80.2265, 12.9865], [80.2280, 12.9868]]},

    # OHT-Admin & Health Gravity Mains
    {"id": "PIPE-A-01", "from_node": "OHT-ADMIN", "to_node": "BLK-04", "diameter_mm": 75, "length_m": 210.0,
     "coordinates": [[80.2225, 12.9858], [80.2235, 12.9875]]},
    {"id": "PIPE-A-02", "from_node": "OHT-ADMIN", "to_node": "BLK-05", "diameter_mm": 75, "length_m": 205.0,
     "coordinates": [[80.2225, 12.9858], [80.2241, 12.9868]]},
    {"id": "PIPE-A-03", "from_node": "OHT-ADMIN", "to_node": "BLK-10", "diameter_mm": 75, "length_m": 170.0,
     "coordinates": [[80.2225, 12.9858], [80.2215, 12.9870]]},
    {"id": "PIPE-A-04", "from_node": "OHT-ADMIN", "to_node": "BLK-13", "diameter_mm": 75, "length_m": 170.0,
     "coordinates": [[80.2225, 12.9858], [80.2210, 12.9855]]},
    {"id": "PIPE-A-05", "from_node": "OHT-ADMIN", "to_node": "BLK-14", "diameter_mm": 50, "length_m": 185.0,
     "coordinates": [[80.2225, 12.9858], [80.2230, 12.9842]]},
    {"id": "PIPE-A-06", "from_node": "OHT-ADMIN", "to_node": "BLK-18", "diameter_mm": 50, "length_m": 690.0,
     "coordinates": [[80.2225, 12.9858], [80.2165, 12.9840]]},
    {"id": "PIPE-A-07", "from_node": "OHT-ADMIN", "to_node": "BLK-20", "diameter_mm": 75, "length_m": 410.0,
     "coordinates": [[80.2225, 12.9858], [80.2250, 12.9830]]},
]

