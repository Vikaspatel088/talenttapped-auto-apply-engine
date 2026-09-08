from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from api.routes import router
from engine.core import event_bus

app = FastAPI(title="Auto-Apply Engine", version="1.0.0", description="Automatically fills and submits job applications from a candidate profile.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

@app.get("/events")
async def sse_events(request: Request):
    async def generator():
        async for chunk in event_bus.subscribe():
            if await request.is_disconnected(): break
            yield chunk
    return StreamingResponse(generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.get("/health")
async def health(): return {"status": "ok"}
