from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
_queues: list[asyncio.Queue] = []
_lock = asyncio.Lock()

async def _add_queue(q: asyncio.Queue) -> None:
    async with _lock: _queues.append(q)

async def _remove_queue(q: asyncio.Queue) -> None:
    async with _lock:
        try: _queues.remove(q)
        except ValueError: pass

def emit(run_id: str, status: str, payload: dict) -> None:
    event = {"run_id": run_id, "status": status, "payload": payload}
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running(): asyncio.run_coroutine_threadsafe(_broadcast(event), loop)
    except RuntimeError: logger.warning("event_bus.emit: no running event loop")

async def _broadcast(event: dict) -> None:
    async with _lock: active = list(_queues)
    for q in active:
        try: q.put_nowait(event)
        except asyncio.QueueFull: logger.warning("SSE queue full")

async def subscribe() -> AsyncGenerator[str, None]:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    await _add_queue(q)
    try:
        while True:
            event = await q.get()
            yield f"event: apply_update\ndata: {json.dumps(event)}\n\n"
    except asyncio.CancelledError: pass
    finally: await _remove_queue(q)
