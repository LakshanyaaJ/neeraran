"""
Script to generate /apps/api/data/campus.geojson
Campus footprint near Erode, Tamil Nadu (~11.345 N, 77.728 E).
Contains:
- 20 Block Polygons
- Points for Sump, 4 Overhead Tanks, 2 Borewells, 1 Municipal Inlet
- Lines for Main Pipe segments with node IDs
"""
import json

CAMPUS_LNG = 77.7280
CAMPUS_LAT = 11.3450

def make_poly(center_lng, center_lat, w=0.0008, h=0.0006):
    return [
        [
            [round(center_lng - w/2, 6), round(center_lat - h/2, 6)],
            [round(center_lng + w/2, 6), round(center_lat - h/2, 6)],
            [round(center_lng + w/2, 6), round(center_lat + h/2, 6)],
            [round(center_lng - w/2, 6), round(center_lat + h/2, 6)],
            [round(center_lng - w/2, 6), round(center_lat - h/2, 6)],
        ]
    ]

# 20 Blocks
BLOCKS = [
    {
        "id": "BLK-01", "name": "Cauvery Boys Hostel", "code": "CBH", "type": "residential",
        "population": 850, "vulnerable": True, "design_daily_demand_l": 114750,
        "fed_by": "OHT-HOSTEL", "center": [CAMPUS_LNG - 0.0035, CAMPUS_LAT + 0.0022]
    },
    {
        "id": "BLK-02", "name": "Krishna Boys Hostel", "code": "KBH", "type": "residential",
        "population": 750, "vulnerable": True, "design_daily_demand_l": 101250,
        "fed_by": "OHT-HOSTEL", "center": [CAMPUS_LNG - 0.0022, CAMPUS_LAT + 0.0031]
    },
    {
        "id": "BLK-03", "name": "Vaigai Girls Hostel", "code": "VGH", "type": "residential",
        "population": 900, "vulnerable": True, "design_daily_demand_l": 121500,
        "fed_by": "OHT-HOSTEL", "center": [CAMPUS_LNG - 0.0048, CAMPUS_LAT + 0.0010]
    },
    {
        "id": "BLK-04", "name": "Campus Health Centre", "code": "HLC", "type": "health",
        "population": 35, "vulnerable": True, "design_daily_demand_l": 25000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG + 0.0015, CAMPUS_LAT + 0.0005]
    },
    {
        "id": "BLK-05", "name": "Campus Daycare & Crèche", "code": "CRC", "type": "crèche",
        "population": 45, "vulnerable": True, "design_daily_demand_l": 18000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG + 0.0021, CAMPUS_LAT - 0.0002]
    },
    {
        "id": "BLK-06", "name": "Central Mess Complex", "code": "MES", "type": "mess",
        "population": 2500, "vulnerable": False, "design_daily_demand_l": 150000,
        "fed_by": "OHT-HOSTEL", "center": [CAMPUS_LNG - 0.0015, CAMPUS_LAT + 0.0015]
    },
    {
        "id": "BLK-07", "name": "Ramanujan Hall (Acad A)", "code": "ACA", "type": "academic",
        "population": 1800, "vulnerable": False, "design_daily_demand_l": 81000,
        "fed_by": "OHT-NORTH", "center": [CAMPUS_LNG + 0.0005, CAMPUS_LAT + 0.0045]
    },
    {
        "id": "BLK-08", "name": "Sir C.V. Raman Science Block (Acad B)", "code": "ACB", "type": "academic",
        "population": 1400, "vulnerable": False, "design_daily_demand_l": 95000,
        "fed_by": "OHT-NORTH", "center": [CAMPUS_LNG + 0.0020, CAMPUS_LAT + 0.0052]
    },
    {
        "id": "BLK-09", "name": "Alan Turing Computing Complex (Acad C)", "code": "ACC", "type": "academic",
        "population": 1600, "vulnerable": False, "design_daily_demand_l": 72000,
        "fed_by": "OHT-NORTH", "center": [CAMPUS_LNG + 0.0035, CAMPUS_LAT + 0.0040]
    },
    {
        "id": "BLK-10", "name": "Central Library & Knowledge Centre", "code": "LIB", "type": "library",
        "population": 600, "vulnerable": False, "design_daily_demand_l": 32000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0000]
    },
    {
        "id": "BLK-11", "name": "Nanotech & Advanced Research Labs", "code": "LAB", "type": "labs",
        "population": 250, "vulnerable": False, "design_daily_demand_l": 65000,
        "fed_by": "OHT-SOUTH", "center": [CAMPUS_LNG + 0.0040, CAMPUS_LAT + 0.0010]
    },
    {
        "id": "BLK-12", "name": "Aquatics & Sports Ground Complex", "code": "SPT", "type": "sports ground",
        "population": 400, "vulnerable": False, "design_daily_demand_l": 75000,
        "fed_by": "OHT-SOUTH", "center": [CAMPUS_LNG + 0.0052, CAMPUS_LAT - 0.0025]
    },
    {
        "id": "BLK-13", "name": "Administrative Bhavan", "code": "ADM", "type": "academic",
        "population": 300, "vulnerable": False, "design_daily_demand_l": 30000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG - 0.0010, CAMPUS_LAT - 0.0015]
    },
    {
        "id": "BLK-14", "name": "Executive Guest House", "code": "GHS", "type": "residential",
        "population": 60, "vulnerable": False, "design_daily_demand_l": 24000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG + 0.0010, CAMPUS_LAT - 0.0028]
    },
    {
        "id": "BLK-15", "name": "Student Activity Centre (SAC)", "code": "SAC", "type": "sports ground",
        "population": 500, "vulnerable": False, "design_daily_demand_l": 45000,
        "fed_by": "OHT-SOUTH", "center": [CAMPUS_LNG + 0.0030, CAMPUS_LAT - 0.0018]
    },
    {
        "id": "BLK-16", "name": "Workshop & Fabrication Hub", "code": "WKS", "type": "academic",
        "population": 220, "vulnerable": False, "design_daily_demand_l": 35000,
        "fed_by": "OHT-NORTH", "center": [CAMPUS_LNG + 0.0050, CAMPUS_LAT + 0.0032]
    },
    {
        "id": "BLK-17", "name": "Substation & Electrical Annex", "code": "UTL", "type": "academic",
        "population": 50, "vulnerable": False, "design_daily_demand_l": 15000,
        "fed_by": "OHT-SOUTH", "center": [CAMPUS_LNG + 0.0060, CAMPUS_LAT - 0.0002]
    },
    {
        "id": "BLK-18", "name": "Main Entrance Security Hub", "code": "SEC", "type": "academic",
        "population": 30, "vulnerable": False, "design_daily_demand_l": 10000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG - 0.0055, CAMPUS_LAT - 0.0030]
    },
    {
        "id": "BLK-19", "name": "Campus Food Plaza & Cafeteria", "code": "CAF", "type": "mess",
        "population": 350, "vulnerable": False, "design_daily_demand_l": 40000,
        "fed_by": "OHT-HOSTEL", "center": [CAMPUS_LNG - 0.0030, CAMPUS_LAT - 0.0005]
    },
    {
        "id": "BLK-20", "name": "Faculty Residential Enclave", "code": "FAC", "type": "residential",
        "population": 400, "vulnerable": False, "design_daily_demand_l": 60000,
        "fed_by": "OHT-ADMIN", "center": [CAMPUS_LNG + 0.0030, CAMPUS_LAT - 0.0040]
    },
]

# Points for Infrastructure
INFRA_POINTS = [
    {
        "id": "SUMP-MAIN", "name": "Central Campus Water Sump", "type": "sump",
        "capacity_kl": 500.0, "coordinates": [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010]
    },
    {
        "id": "OHT-HOSTEL", "name": "Overhead Tank Hostels", "type": "tank",
        "capacity_kl": 100.0, "coordinates": [CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018]
    },
    {
        "id": "OHT-NORTH", "name": "Overhead Tank North Academic", "type": "tank",
        "capacity_kl": 80.0, "coordinates": [CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048]
    },
    {
        "id": "OHT-SOUTH", "name": "Overhead Tank South Labs", "type": "tank",
        "capacity_kl": 80.0, "coordinates": [CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005]
    },
    {
        "id": "OHT-ADMIN", "name": "Overhead Tank Admin & Health", "type": "tank",
        "capacity_kl": 60.0, "coordinates": [CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012]
    },
    {
        "id": "BW-01", "name": "Deep Borewell 1 (North Aquifer)", "type": "borewell",
        "max_yield_lpm": 250.0, "coordinates": [CAMPUS_LNG - 0.0020, CAMPUS_LAT + 0.0060]
    },
    {
        "id": "BW-02", "name": "Deep Borewell 2 (South Aquifer)", "type": "borewell",
        "max_yield_lpm": 200.0, "coordinates": [CAMPUS_LNG + 0.0065, CAMPUS_LAT - 0.0035]
    },
    {
        "id": "MUNI-INLET-01", "name": "Erode Municipal Water Board Inlet", "type": "municipal_inlet",
        "allocation_kld": 150.0, "coordinates": [CAMPUS_LNG - 0.0070, CAMPUS_LAT - 0.0010]
    },
    {
        "id": "STP-MAIN", "name": "Campus Greywater Reclamation Plant (STP)", "type": "STP",
        "capacity_kld": 150.0, "coordinates": [CAMPUS_LNG + 0.0070, CAMPUS_LAT + 0.0020]
    }
]

# Lines for main pipe network
PIPES = [
    # Inflow sources to Sump
    {"id": "PIPE-BW1", "from_node": "BW-01", "to_node": "SUMP-MAIN", "diameter_mm": 150, "length_m": 580.0,
     "coordinates": [[CAMPUS_LNG - 0.0020, CAMPUS_LAT + 0.0060], [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010]]},
    {"id": "PIPE-BW2", "from_node": "BW-02", "to_node": "SUMP-MAIN", "diameter_mm": 150, "length_m": 920.0,
     "coordinates": [[CAMPUS_LNG + 0.0065, CAMPUS_LAT - 0.0035], [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010]]},
    {"id": "PIPE-MUN", "from_node": "MUNI-INLET-01", "to_node": "SUMP-MAIN", "diameter_mm": 200, "length_m": 710.0,
     "coordinates": [[CAMPUS_LNG - 0.0070, CAMPUS_LAT - 0.0010], [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010]]},

    # Sump to Tanks pumping mains
    {"id": "PIPE-P1-OHTH", "from_node": "SUMP-MAIN", "to_node": "OHT-HOSTEL", "diameter_mm": 200, "length_m": 240.0,
     "coordinates": [[CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010], [CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018]]},
    {"id": "PIPE-P2-OHTN", "from_node": "SUMP-MAIN", "to_node": "OHT-NORTH", "diameter_mm": 150, "length_m": 480.0,
     "coordinates": [[CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010], [CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048]]},
    {"id": "PIPE-P3-OHTS", "from_node": "SUMP-MAIN", "to_node": "OHT-SOUTH", "diameter_mm": 150, "length_m": 570.0,
     "coordinates": [[CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010], [CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005]]},
    {"id": "PIPE-P4-OHTA", "from_node": "SUMP-MAIN", "to_node": "OHT-ADMIN", "diameter_mm": 125, "length_m": 260.0,
     "coordinates": [[CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0010], [CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012]]},

    # Distribution lines from Tanks to Blocks
    {"id": "PIPE-H-01", "from_node": "OHT-HOSTEL", "to_node": "BLK-01", "diameter_mm": 100, "length_m": 120.0,
     "coordinates": [[CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018], [CAMPUS_LNG - 0.0035, CAMPUS_LAT + 0.0022]]},
    {"id": "PIPE-H-02", "from_node": "OHT-HOSTEL", "to_node": "BLK-02", "diameter_mm": 100, "length_m": 150.0,
     "coordinates": [[CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018], [CAMPUS_LNG - 0.0022, CAMPUS_LAT + 0.0031]]},
    {"id": "PIPE-H-03", "from_node": "OHT-HOSTEL", "to_node": "BLK-03", "diameter_mm": 100, "length_m": 270.0,
     "coordinates": [[CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018], [CAMPUS_LNG - 0.0048, CAMPUS_LAT + 0.0010]]},
    {"id": "PIPE-H-04", "from_node": "OHT-HOSTEL", "to_node": "BLK-06", "diameter_mm": 125, "length_m": 115.0,
     "coordinates": [[CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018], [CAMPUS_LNG - 0.0015, CAMPUS_LAT + 0.0015]]},
    {"id": "PIPE-H-05", "from_node": "OHT-HOSTEL", "to_node": "BLK-19", "diameter_mm": 75, "length_m": 260.0,
     "coordinates": [[CAMPUS_LNG - 0.0025, CAMPUS_LAT + 0.0018], [CAMPUS_LNG - 0.0030, CAMPUS_LAT - 0.0005]]},

    {"id": "PIPE-N-01", "from_node": "OHT-NORTH", "to_node": "BLK-07", "diameter_mm": 100, "length_m": 150.0,
     "coordinates": [[CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048], [CAMPUS_LNG + 0.0005, CAMPUS_LAT + 0.0045]]},
    {"id": "PIPE-N-02", "from_node": "OHT-NORTH", "to_node": "BLK-08", "diameter_mm": 100, "length_m": 60.0,
     "coordinates": [[CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048], [CAMPUS_LNG + 0.0020, CAMPUS_LAT + 0.0052]]},
    {"id": "PIPE-N-03", "from_node": "OHT-NORTH", "to_node": "BLK-09", "diameter_mm": 100, "length_m": 210.0,
     "coordinates": [[CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048], [CAMPUS_LNG + 0.0035, CAMPUS_LAT + 0.0040]]},
    {"id": "PIPE-N-04", "from_node": "OHT-NORTH", "to_node": "BLK-16", "diameter_mm": 75, "length_m": 380.0,
     "coordinates": [[CAMPUS_LNG + 0.0018, CAMPUS_LAT + 0.0048], [CAMPUS_LNG + 0.0050, CAMPUS_LAT + 0.0032]]},

    {"id": "PIPE-S-01", "from_node": "OHT-SOUTH", "to_node": "BLK-11", "diameter_mm": 100, "length_m": 175.0,
     "coordinates": [[CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005], [CAMPUS_LNG + 0.0040, CAMPUS_LAT + 0.0010]]},
    {"id": "PIPE-S-02", "from_node": "OHT-SOUTH", "to_node": "BLK-12", "diameter_mm": 100, "length_m": 235.0,
     "coordinates": [[CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005], [CAMPUS_LNG + 0.0052, CAMPUS_LAT - 0.0025]]},
    {"id": "PIPE-S-03", "from_node": "OHT-SOUTH", "to_node": "BLK-15", "diameter_mm": 75, "length_m": 210.0,
     "coordinates": [[CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005], [CAMPUS_LNG + 0.0030, CAMPUS_LAT - 0.0018]]},
    {"id": "PIPE-S-04", "from_node": "OHT-SOUTH", "to_node": "BLK-17", "diameter_mm": 50, "length_m": 165.0,
     "coordinates": [[CAMPUS_LNG + 0.0045, CAMPUS_LAT - 0.0005], [CAMPUS_LNG + 0.0060, CAMPUS_LAT - 0.0002]]},

    {"id": "PIPE-A-01", "from_node": "OHT-ADMIN", "to_node": "BLK-04", "diameter_mm": 75, "length_m": 210.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG + 0.0015, CAMPUS_LAT + 0.0005]]},
    {"id": "PIPE-A-02", "from_node": "OHT-ADMIN", "to_node": "BLK-05", "diameter_mm": 75, "length_m": 205.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG + 0.0021, CAMPUS_LAT - 0.0002]]},
    {"id": "PIPE-A-03", "from_node": "OHT-ADMIN", "to_node": "BLK-10", "diameter_mm": 75, "length_m": 170.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG - 0.0005, CAMPUS_LAT + 0.0000]]},
    {"id": "PIPE-A-04", "from_node": "OHT-ADMIN", "to_node": "BLK-13", "diameter_mm": 75, "length_m": 170.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG - 0.0010, CAMPUS_LAT - 0.0015]]},
    {"id": "PIPE-A-05", "from_node": "OHT-ADMIN", "to_node": "BLK-14", "diameter_mm": 50, "length_m": 185.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG + 0.0010, CAMPUS_LAT - 0.0028]]},
    {"id": "PIPE-A-06", "from_node": "OHT-ADMIN", "to_node": "BLK-18", "diameter_mm": 50, "length_m": 690.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG - 0.0055, CAMPUS_LAT - 0.0030]]},
    {"id": "PIPE-A-07", "from_node": "OHT-ADMIN", "to_node": "BLK-20", "diameter_mm": 75, "length_m": 410.0,
     "coordinates": [[CAMPUS_LNG + 0.0005, CAMPUS_LAT - 0.0012], [CAMPUS_LNG + 0.0030, CAMPUS_LAT - 0.0040]]},

    # STP Recycled water line to Sports ground
    {"id": "PIPE-STP-SPT", "from_node": "STP-MAIN", "to_node": "BLK-12", "diameter_mm": 100, "length_m": 520.0,
     "coordinates": [[CAMPUS_LNG + 0.0070, CAMPUS_LAT + 0.0020], [CAMPUS_LNG + 0.0052, CAMPUS_LAT - 0.0025]]}
]

features = []

# 1. Blocks as Polygons
for b in BLOCKS:
    poly_coords = make_poly(b["center"][0], b["center"][1])
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": poly_coords
        },
        "properties": {
            "id": b["id"],
            "name": b["name"],
            "code": b["code"],
            "type": b["type"],
            "population": b["population"],
            "vulnerable": b["vulnerable"],
            "design_daily_demand_l": b["design_daily_demand_l"],
            "fed_by": b["fed_by"],
            "center": b["center"]
        }
    })

# 2. Infra Points
for p in INFRA_POINTS:
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": p["coordinates"]
        },
        "properties": {
            "id": p["id"],
            "name": p["name"],
            "type": p["type"],
            "capacity_kl": p.get("capacity_kl"),
            "max_yield_lpm": p.get("max_yield_lpm"),
            "allocation_kld": p.get("allocation_kld")
        }
    })

# 3. Pipes as LineStrings
for line in PIPES:
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": line["coordinates"]
        },
        "properties": {
            "id": line["id"],
            "from_node": line["from_node"],
            "to_node": line["to_node"],
            "diameter_mm": line["diameter_mm"],
            "length_m": line["length_m"],
            "type": "pipe"
        }
    })

geojson_data = {
    "type": "FeatureCollection",
    "metadata": {
        "campus_name": "Kongu Educational Campus Twin",
        "location": "Near Perundurai-Erode Corridor, Tamil Nadu, India",
        "coordinates": [CAMPUS_LNG, CAMPUS_LAT],
        "blocks_count": len(BLOCKS),
        "infra_points_count": len(INFRA_POINTS),
        "pipe_lines_count": len(PIPES)
    },
    "features": features
}

with open("apps/api/data/campus.geojson", "w") as f:
    json.dump(geojson_data, f, indent=2)

print("Created /apps/api/data/campus.geojson successfully!")
