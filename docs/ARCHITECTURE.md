# NEERARAN (நீர்Aran) — System Architecture & Data Engineering

This document details the software engineering architecture, agent pipelines, simulation loops, fail-safe protocols, and known operational limits of NEERARAN.

---

## 1. End-to-End Processing Architecture

The system operates across a strict 7-stage pipeline:

```mermaid
flowchart LR
    Input["1. INPUT<br/>Reservoirs, Sump,<br/>Meters, Weather,<br/>Complaints, Sensors"] 
    --> Agents["2. AGENTS<br/>Monitor, Detector,<br/>Localizer, Forecaster,<br/>Prioritizer, Optimizer"]
    --> Tools["3. TOOLS<br/>Simulated SCADA Valve,<br/>Pump Actuator, CMMS,<br/>Public Notice Drafter"]
    --> Data["4. DATA<br/>Digital Twin State,<br/>Baseline History,<br/>Evidence Artifacts"]
    --> Decisions["5. DECISIONS<br/>Ranked Actions,<br/>LP Schedules,<br/>Multi-Step Plans"]
    --> HumanControl["6. HUMAN CONTROL<br/>Estate Admin Approval,<br/>Vulnerable Guardrail,<br/>1-Click Rollback"]
    --> Output["7. OUTPUT<br/>Telemetry Actuation,<br/>Work Orders Dispatched,<br/>Measured kL Saved"]
```

---

## 2. Seven-Stage Agent Operational Loop

```mermaid
graph LR
    M["1. MONITOR<br/>Quality, Stale, Flatlines"] --> D["2. DETECT<br/>IsolationForest + MNF"]
    D --> L["3. LOCALIZE<br/>Mass Balance + Pressure Drop"]
    L --> P["4. PREDICT<br/>Holt-Winters 72h Reserve"]
    P --> PR["5. PRIORITIZE<br/>AHP Multi-Term Ranking"]
    PR --> O["6. OPTIMIZE<br/>scipy.linprog Tariff Schedule"]
    O --> I["7. INTERVENE<br/>SCADA & CMMS Work Orders"]
    I --> V["VERIFIER<br/>Grounding Audit & Guardrails"]
    V -.->|Measured Baseline| M
```

---

## 3. High-Level Subsystem Layout

```mermaid
flowchart TD
    subgraph Client ["Frontend: React 18 + Vite + TypeScript (apps/web)"]
        Landing["Landing Page (Smooth Scroll, Parallax Clouds)"]
        DemoGate["RBAC Gate (Estate Admin / Viewer)"]
        AppShell["Bento Dashboard Shell"]
        
        subgraph Views ["Operational Views"]
            Overview["Overview Cockpit"]
            MapTwin["MapLibre 2.5D Digital Twin Map"]
            AgentsView["7-Agent Multi-Trace Timeline"]
            ApprovalsView["Human Approval Clearance Queue"]
            SimControls["Simulation & Scenario Injector"]
            EvalView["Ground-Truth Benchmark Matrix"]
            RespAI["Responsible AI & Guardrails"]
        end
        
        subgraph ClientResilience ["Client Data Resilience"]
            ApiClient["API Client Wrapper (4s Timeout, 1 Retry)"]
            DemoSafeToggle["Demo Safe Mode (Shift+D Toggle)"]
            FallbackSnapshot["Fallback Snapshot Engine (/public/fallback)"]
            StatusPill["Live / Demo safe mode / Degraded / Offline Pill"]
        end
    end

    subgraph Backend ["Backend: FastAPI Python 3.13 (apps/api)"]
        SimEngine["Digital Twin Physical Simulator (Deterministic Seed 42)"]
        
        subgraph AgentCore ["Agentic Orchestration"]
            MonitorAgent["Monitor (Sensor Quality & Dropout Imputation)"]
            DetectorAgent["Detector (Minimum Night Flow z-Score & IsolationForest)"]
            LocalizerAgent["Localizer (Zone Mass Balance & Pressure Gradient)"]
            ForecasterAgent["Forecaster (Holt-Winters Diurnal & Weather Correction)"]
            PrioritizerAgent["Prioritizer (Dynamic Multi-Criteria Loss Scoring)"]
            OptimizerAgent["Optimizer (Dual-Tariff Linear Programming Pump Scheduler)"]
            InterventorAgent["Interventor (SCADA, CMMS & Rollback Synthesis)"]
            VerifierAgent["Verifier (Evidence ID Grounding & Vulnerable Guardrail)"]
        end
        
        subgraph DB ["Persistence & Immutable Audit"]
            SQLiteDB["SQLite SQLModel (AuditLog, ApprovalItem, GroundTruth)"]
        end
        
        SSE["Server-Sent Events Telemetry Stream"]
    end

    Landing --> DemoGate
    DemoGate --> AppShell
    AppShell --> Views
    Views --> ApiClient
    ApiClient -->|REST & SSE| Backend
    ApiClient -.->|Network Partition / Shift+D| FallbackSnapshot
    SimEngine --> SSE
    SimEngine --> AgentCore
    AgentCore --> SQLiteDB
```

---

## 4. Synthetic Campus Digital Twin Network Topology

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

## 5. Known Operational Limitations

To maintain scientific integrity and transparent engineering standards, NEERARAN explicitly documents the boundary conditions of its digital twin:

1. **Sub-Threshold Pinhole Weepage (< 5.0 L/min)**:
   - Flow perturbations smaller than 5.0 L/min are masked by normal background sensor variance in 5-minute meter sampling intervals.
   - *Mitigation*: These require acoustic pipe listening rods or correlation leak sensors during physical surveys.
2. **High-Frequency Hydraulic Transients (< 2.0 Seconds)**:
   - Sudden water-hammer pressure spikes lasting milliseconds (e.g., rapid solenoid valve closures) fall outside the 5-minute macroscopic digital twin interval.
   - *Mitigation*: Physical surge relief vessels and check valves protect field equipment.
3. **Severe Sensor Cluster Dropouts (> 60% Blackout)**:
   - If over 60% of telemetry meters in a single zone simultaneously lose telemetry or fail, localized hydraulic gradient precision drops to zone-level mass conservation.
   - *Mitigation*: System generates immediate `DATA_QUALITY_ISSUE` alerts and flags localized segment rankings as provisional.
4. **Autonomous Water Quality Remediation**:
   - The platform accurately identifies quality anomalies from turbidity, chlorine, and pH sensors, but does not autonomously actuate chemical dosing without certified lab titration.
   - *Mitigation*: Generates immediate health advisory tickets to the Chief Medical Officer and Estates Office.
