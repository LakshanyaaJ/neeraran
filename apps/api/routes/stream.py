"""
Server-Sent Events (SSE) Live Simulation Stream — Phase 3
Streams one telemetry tick message per step.
Optimized for zero-leak continuous operation.
"""
import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..sim.engine import sim_engine

router = APIRouter(tags=["stream"])

@router.get("/api/stream")
@router.get("/api/sim/stream")
async def simulation_stream(request: Request):
    """
    Continuous real-time SSE stream sending simulation telemetry to clients.
    Emits 1 message per tick.
    """
    async def event_generator():
        try:
            while True:
                # Check client connection status
                if await request.is_disconnected():
                    break

                # If simulation is active, step 1 tick (5 minutes)
                if not sim_engine.is_paused:
                    sim_engine.tick(steps=1)

                state = sim_engine.get_state()
                yield {
                    "event": "tick",
                    "data": json.dumps(state)
                }

                # 1.0 second delay between ticks in stream
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(event_generator())
