# NEERARAN (நீர்Aran) — Master Specification & Product Requirements

> **Challenge**: TCS Tech Day — Challenge 12: AI for Water Resilience & Smart Resource Management  
> **Tagline**: *"Every drop accounted for."*  
> **Branding**: நீர் (Tamil: *Neer* = Water) + Aran (Tamil/English: *Aran* = Fortress / Shield). Together: *The Water Fortress*.

---

## 1. Product Mission & Operational Scope

NEERARAN is an enterprise-grade AI resilience and autonomous decision-support system designed for educational and commercial campuses. Unlike typical consumption dashboards that merely graph historical water volume, NEERARAN executes a continuous, autonomous operational loop:

$$\text{Monitor} \longrightarrow \text{Detect} \longrightarrow \text{Predict} \longrightarrow \text{Prioritize} \longrightarrow \text{Optimize} \longrightarrow \text{Intervene} \longrightarrow \text{Measure}$$

At every screen and operational junction, the platform directly answers three core engineering questions:
1. **What to do next?** (Ordered, verified action recommendations)
2. **Where to do it?** (Precise digital twin geo-coordinates, block, pipe segment, or valve)
3. **Why do it?** (Transparent evidence IDs linking sensor readouts, weather data, and history)

All metrics, sensor flows, reservoir levels, and pressure graphs are computed deterministically from the digital twin simulator and agent reasoners; **no numbers are ever hardcoded**.

---

## 2. Synthetic Campus Digital Twin Topology (20 Blocks & Assets)

The platform models an educational campus (e.g. 10,000 residents, staff, and day scholars) with high fidelity:

### Residential & Sensitive Facilities (Vulnerable Zones)
1. **Cauvery Boys Hostel** (Block 1) — 850 residents. *Vulnerable Zone*.
2. **Krishna Boys Hostel** (Block 2) — 750 residents. *Vulnerable Zone*.
3. **Vaigai Girls Hostel** (Block 3) — 900 residents. *Vulnerable Zone*.
4. **Campus Health Centre** (Block 4) — 24/7 clinic, 12 inpatient beds. *Strict Vulnerable Zone*.
5. **Campus Daycare & Crèche** (Block 5) — 45 children of faculty/staff. *Strict Vulnerable Zone*.

### Academic & Research
6. **Ramanujan Hall (Academic Block A)** — Mathematics & Computer Science.
7. **Sir C.V. Raman Science Block (Academic Block B)** — Physics, Chemistry & Wet Laboratories.
8. **Alan Turing Computing Complex (Academic Block C)** — Data Centers, High Performance Computing.
9. **Central Library & Knowledge Resource Centre** — 4-storey reading hall & archive.
10. **Advanced Materials & Nanotech Research Facility** — Cleanrooms and de-ionised water loops.

### Campus Utilities & Dining
11. **Central Mess & Dining Complex** — Prepares ~9,000 meals daily; high kitchen water load.
12. **Student Activity Centre (SAC) & Indoor Arena** — Gym, indoor courts, changing facilities.
13. **Olympic Aquatic Centre & Outdoor Sports Pavilion** — 50m swimming pool and field irrigation.
14. **Administrative Bhavan** — Chancellor/Registrar offices, finance, estate operations.
15. **Campus Guest House & Executive MDP Residence** — 40 suites.

### Water Infrastructure Network
16. **Main Campus Underground Sump (UG Sump)** — 500 kL raw water buffer reservoir with dual intake.
17. **Overhead Tank North (OHT-North)** — 80 kL elevated storage tank serving academic blocks.
18. **Overhead Tank South (OHT-South)** — 80 kL elevated storage tank serving labs and sports complex.
19. **Overhead Tank Hostels (OHT-Hostel)** — 100 kL dedicated storage tank for residential hostels.
20. **Overhead Tank Admin (OHT-Admin)** — 60 kL tank serving library, admin, health centre, and guest house.
21. **Deep Borewell 1 (North Aquifer)** — 180m depth, submersible variable-frequency pump (250 L/min).
22. **Deep Borewell 2 (South Aquifer)** — 210m depth, submersible variable-frequency pump (200 L/min).
23. **Sewage Treatment & Greywater Reclamation Plant (STP)** — 150 kL/day capacity, tertiary filter with dual distribution to campus landscaping and sports grounds.

---

## 3. Seven Jury-Scored Capabilities

| # | Capability | Implementation Mechanism |
|---|---|---|
| **1** | **Reason across sources** | Ingests reservoir levels, weather forecast, ultrasonic block flow meters, piezoresistive pipe pressure sensors, maintenance logs, and student complaints into a unified ontology. |
| **2** | **Plan multi-step** | Autonomous planner agent structures actionable remediation plans with sequential dependencies, rollback gates, and estimated completion times. |
| **3** | **Act through tools** | Dispatches simulated CMMS repair work orders, issues SCADA pump/valve commands, and drafts public campus advisories. |
| **4** | **Verify against evidence** | Verifier Agent audits every proposition against specific `EVID-...` identifiers; propositions lacking evidence are rejected. |
| **5** | **Adapt dynamically** | Scenario injector triggers sudden events (pipe rupture, borewell failure, unseasonal rainfall, sports day surge) causing immediate re-planning. |
| **6** | **Human control & Guardrails** | Consequential actions (pressure modulation, zone rationing) await Estate Admin approval. Vulnerable zones enforce mandatory equity impact audits. |
| **7** | **Evaluate against ground truth** | Real-time quantitative scoring benchmark comparing detected leaks, flow discrepancies, and forecast errors against simulator ground truth. |

---

## 4. Users, RBAC & Context Lenses

1. **Estate Admin (Estate Manager)**:
   - Unrestricted operational control.
   - Authorizes high-consequence interventions in the Approval Queue.
   - Adjusts algorithmic sensitivity thresholds and executes what-if scenario simulations.
2. **Viewer**:
   - Read-only operational oversight with zero approval buttons or scenario modification privileges.
   - Can toggle between 4 domain lenses:
     - **Warden Lens**: Focuses on hostel tank headrooms, mess meal-prep water reserves, and night-flow leak flags.
     - **Sustainability Lens**: Tracks water conservation index (kL saved), STP greywater recycling efficiency, energy per kL pumped, and statutory compliance.
     - **Student Advisory Lens**: Displays plain, public-friendly water quality reports, scheduled maintenance notices, and conservation tips.
     - **Maintenance Lens**: Highlights the open CMMS ticket queue, pipe stress indicators, valve health telemetry, and technician dispatch statuses.

---

## 5. Design System & Anti-AI Human Design Rules

### Custom Color Palette
```css
:root {
  --color-sky-50:  #EAF3FD;
  --color-sky-100: #D9E9FB;
  --color-sky-300: #8FC0EE;
  --color-sky-500: #3A8FDA;
  --color-sky-700: #1E5FA8;
  --color-ink-900: #0F2236;
  --color-ink-600: #4A5F75;
  --color-mist:    #F2F6FA;
  --color-aqua:    #2FB8AA; /* Normal operational baseline */
  --color-leaf:    #4CBF86; /* Positive resilience / savings */
  --color-amber:   #F2A33A; /* Watch / Advisory */
  --color-coral:   #E5594F; /* Anomaly / Leak / Critical */
  
  --glass-bg: rgba(255, 255, 255, 0.55);
  --glass-border: rgba(255, 255, 255, 0.70);
  --glass-blur: 18px;
}
```

### Strict Human-Crafted Aesthetic Principles
- **No AI clichés**: No purple/indigo/violet, no emoji icons, no glowing orbs or floating particles, no all-caps tracking, no icon-in-a-colored-circle badges.
- **Bare typography**: All icons use bare 1.5px stroke Lucide SVGs placed inline.
- **Typography hierarchy**: Onest for Latin headings and body, Anek Tamil for Tamil typography (`நீர்`), JetBrains Mono strictly for telemetry readouts.
- **Asymmetric Bento layout**: Varied card dimensions and visual weighting rather than monotonous identical cards.
- **Physical craft details**: Real campus engineering vocabulary (e.g., *Headloss at Junction J-04*, *Sump raw inflow 4.2 L/s*), hand-drawn subtle accent marks, and an authentic simulated data indicator.
