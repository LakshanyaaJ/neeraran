"""
Server-Sent Events (SSE) live simulation tick stream.
"""
import asyncio
import json
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ..sim.engine import simulator_instance

router = APIRouter(prefix="/api/sim", tags=["stream"])

@router.get("/stream")
async def simulation_stream(request: Request):
    """
    Continuous real-time SSE stream sending simulation telemetry to clients.
    Automatically steps simulation according to active speed and frequency.
    """
    async def event_generator():
        while True:
            # If client disconnected, break
            if await request.is_disconnected():
                break

            # If not paused, advance simulator tick slightly
            if not simulator_instance.is_paused:
                simulator_instance.tick(elapsed_minutes=0.5)

            state = simulator_instance.get_state()
            yield {
                "event": "tick",
                "data": json.dumps(state.model_dump())
            }

            # Frequency: 1.5 seconds per event emission
            await asyncio.sleep(1.5)

    return EventSourceResponse(event_generator())
