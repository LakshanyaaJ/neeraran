# நீர்Aran (NEERARAN) — Water Fortress
> **"Every drop accounted for."**  
> TCS Tech Day, Challenge 12: AI for Water Resilience & Smart Resource Management

NEERARAN is an enterprise-grade digital twin and autonomous 7-agent water resilience orchestration platform for large educational campuses. It detects nocturnal weepages before tanks empty, forecasts shortages across a 7-day horizon, ranks interventions mathematically, and strictly waits for a human administrator's authorization.

---

## 5-Line Quickstart

```bash
# 1. Clone & enter directory
git clone https://github.com/bhadrik/neeraran.git && cd neeraran

# 2. Install Python & Frontend dependencies
pip install -r requirements.txt && npm install --prefix apps/web

# 3. Start digital twin backend API (port 8000)
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# 4. In a second terminal, start the web interface (port 5173)
npm run dev --prefix apps/web

# 5. Open http://localhost:5173 in your browser (Login as Estate Admin or Viewer)
```

---

## Presentation & Demo Controls
- **Demo Safe Mode**: Press `Shift+D` anywhere in the app to toggle offline fallback mode. Guarantees 0ms dropout during dead Wi-Fi or backend disconnects.
- **Reset Demo**: Click avatar menu (top right) $\rightarrow$ **Reset Demo (Day 1)** to restore seed 42, wipe approvals & audit logs, and return to 08:00 Day 1.
- **Evaluation & Benchmarks**: Visit `/app/evaluation` to run the 20-scenario live benchmark and adjust the $z$-score sensitivity slider in real time.
- **Responsible AI**: Visit `/app/responsible-ai` for verifiable guardrails and exportable immutable CSV audit trails.

---

## Architecture & Verification
- Comprehensive architectural diagram & limits: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Live ground-truth mathematical formulas & benchmarks: [`docs/EVAL.md`](docs/EVAL.md)
- Complete hackathon master specification: [`docs/MASTER.md`](docs/MASTER.md)
- Test suite: `python -m pytest apps/api/tests/ -v`
