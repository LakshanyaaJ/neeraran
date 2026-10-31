"""
NEERARAN (நீர்Aran) — FastAPI Backend Entrypoint — Phase 3
Challenge 12: AI for Water Resilience & Smart Resource Management
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone

from .db.database import init_db
from .routes import campus, simulation, stream
from .sim.seed_history import seed_90_days

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed 90 days of history
    init_db()
    seed_90_days()
    yield

app = FastAPI(
    title="NEERARAN API",
    description="Physical Digital Twin & Agentic Resilience Core for Campus Water Infrastructure",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Vite frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(campus.router)
app.include_router(simulation.router)
app.include_router(stream.router)

@app.get("/")
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "product": "NEERARAN",
        "tagline": "Every drop accounted for.",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": 42,
        "is_simulated": True,
        "note": "All data generated via synthetic digital twin physical simulator."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
