# NEERARAN (நீர்Aran) — System Architecture & Data Engineering

This document outlines the software engineering architecture, agent pipelines, simulation loops, and data resilience protocols powering NEERARAN.

---

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend: React 18 + Vite + TypeScript (apps/web)"]
        Landing["Landing Page (XinoTask UI, Lenis Smooth Scroll)"]
        DemoGate["RBAC Demo Gate (Estate Admin / Viewer)"]
        BentoShell["Bento Dashboard Core Shell"]
        
        subgraph Views ["Operational Lenses & Views"]
            WardenView["Warden Lens"]
            SustainView["Sustainability Lens"]
            StudentView["Student Advisory Lens"]
            MaintView["Maintenance Lens"]
            MapTwin["MapLibre Digital Twin 2.5D Map"]
            SimControls["Sim Scrub & Rate Controller"]
        end
        
        subgraph ClientData ["Client Data Resilience"]
            ApiClient["API Client Wrapper (4s Timeout, 1 Retry)"]
            FallbackSnapshot["Fallback Snapshot Engine (/public/fallback)"]
            StatusPill["Live / Degraded / Offline Status Pill"]
        end
    end

    subgraph Backend ["Backend: FastAPI Python 3.13 (apps/api)"]
        SimEngine["Digital Twin Physical Simulator (Seeded RNG, 10Hz Tick)"]
        
        subgraph Agents ["Reasoning & Autonomous Control"]
            AnomalyAgent["Anomaly & Leak Detector (IsolationForest + Residuals)"]
            ForecasterAgent["Demand Forecaster (Holt-Winters Diurnal Model)"]
            PlannerAgent["Multi-Step Planning Agent (Reasoning Across 6 Sources)"]
            VerifierAgent["Evidence & Guardrail Verifier Agent (Rejects ungrounded claims)"]
            OptimizerAgent["Linear Programming Water Allocator (scipy.optimize.linprog)"]
        end
        
        subgraph ToolSimulators ["Simulated Campus Actuators"]
            SCADASim["SCADA Valve / Pump Actuator"]
            CMMSSim["CMMS Ticket Dispatch Engine"]
            AdvisorySim["Public Notice Drafter"]
        end
        
        subgraph DB ["Persistence & Audit"]
            SQLiteDB["SQLite with SQLModel (Audit Log & Approval Queue)"]
        end
        
        SSE["Server-Sent Events (SSE Stream)"]
    end

    Landing --> DemoGate
    DemoGate --> BentoShell
    BentoShell --> Views
    Views --> ApiClient
    ApiClient -->|REST & SSE| SimEngine
    ApiClient -.->|Network Fail| FallbackSnapshot
    SimEngine --> SSE
    SimEngine --> Agents
    Agents --> ToolSimulators
    Agents --> SQLiteDB
    ToolSimulators --> SQLiteDB
```

---

## 2. Seven-Stage Operational Loop

```mermaid
graph LR
    M["1. MONITOR<br/>Sensors, Tanks, Pressure"] --> D["2. DETECT<br/>IsolationForest Leaks"]
    D --> P["3. PREDICT<br/>Holt-Winters 24h Demand"]
    P --> PR["4. PRIORITIZE<br/>Criticality & Vulnerable Zones"]
    PR --> O["5. OPTIMIZE<br/>scipy.linprog Sump Distribution"]
    O --> I["6. INTERVENE<br/>SCADA & CMMS Actions"]
    I --> ME["7. MEASURE<br/>Ground Truth Evaluation"]
    ME -.->|Feedback Loop| M
```

---

## 3. Synthetic Campus Digital Twin Network Topology

```mermaid
graph TD
    BW1["Borewell 1 (250 L/min)"] -->|Raw Water Line| Sump["Central Campus Sump (500 kL)"]
    BW2["Borewell 2 (200 L/min)"] -->|Raw Water Line| Sump
    Rainfall["Rainfall Inflow"] -->|Harvesting Ring| Sump

    Sump -->|Pump P-1| OHT_Hostel["OHT Hostels (100 kL)"]
    Sump -->|Pump P-2| OHT_North["OHT North Academic (80 kL)"]
    Sump -->|Pump P-3| OHT_South["OHT South Labs & Sports (80 kL)"]
    Sump -->|Pump P-4| OHT_Admin["OHT Admin & Health (60 kL)"]

    OHT_Hostel -->|Gravity Trunk L-1| Cauvery["Cauvery Hostel (Vulnerable)"]
    OHT_Hostel -->|Gravity Trunk L-1| Krishna["Krishna Hostel (Vulnerable)"]
    OHT_Hostel -->|Gravity Trunk L-2| Vaigai["Vaigai Hostel (Vulnerable)"]
    OHT_Hostel -->|Gravity Branch L-3| Mess["Central Mess Complex"]

    OHT_North -->|Gravity Trunk N-1| Ramanujan["Ramanujan Hall (Acad A)"]
    OHT_North -->|Gravity Trunk N-2| Science["Raman Science Block (Acad B)"]
    OHT_North -->|Gravity Trunk N-3| Turing["Turing Computing Block (Acad C)"]

    OHT_South -->|Gravity Trunk S-1| NanoLabs["Nanotech Research Labs"]
    OHT_South -->|Gravity Trunk S-2| SportsAquatics["Aquatic & Sports Complex"]

    OHT_Admin -->|Gravity Trunk A-1| HealthCentre["Health Centre (Strict Vulnerable)"]
    OHT_Admin -->|Gravity Trunk A-1| Creche["Campus Crèche (Strict Vulnerable)"]
    OHT_Admin -->|Gravity Trunk A-2| Library["Central Library"]
    OHT_Admin -->|Gravity Trunk A-2| AdminBhavan["Admin Bhavan & Guest House"]

    Cauvery & Krishna & Vaigai & Mess & Ramanujan & Science & Turing & NanoLabs & SportsAquatics & HealthCentre & Creche & Library & AdminBhavan -->|Grey & Black Discharge| STP["STP Reclamation Plant (150 kL/day)"]
    STP -->|Recycled Water Trunk| Irrigation["Sports Turf & Green Campus Irrigation"]
```

---

## 4. Reliability & Fail-Safe Architecture (Zero Blanks Guarantee)

To meet the strict hackathon uptime and demonstration standard:
1. **Network Wrapper**: The web client uses a unified HTTP wrapper (`/apps/web/src/api/client.ts`) with:
   - 4000ms hard timeout per request.
   - 1 exponential retry attempt.
   - Deterministic transparent fallback to `/public/fallback/snapshot_initial.json`.
2. **State Pill Indication**:
   - `Live` (Active 200 responses and live SSE stream).
   - `Degraded` (Serving offline simulation snapshot cached in public bundle).
   - `Offline` (Network partitioned, read-only cache active).
3. **Seeded Determinism**:
   - Simulator PRNG is initialized with seed `42`.
   - All random walk consumption perturbations and anomaly injections produce identical, reproducible states across judge walkthroughs.

