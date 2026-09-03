"""
What this does: serves the UI and streams the event log over SSE. The frontend is
a pure function of /stream, exactly like the terminal renderer.
What it must never do: compute or invent a number — it only replays what the
pipeline wrote to runs/<run_id>.jsonl.
Where its numbers come from: the event log + the ledger.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .cli import run_demo
from .eventlog import read_log
from .ledger import all_tests, connect

app = FastAPI(title="Thaw")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(FRONTEND.read_text(encoding="utf-8"))


@app.get("/stream")
async def stream(seed: int = 42):
    """Generate a deterministic run, then replay its cards with demo pacing."""
    path = run_demo(seed=seed, speed=10_000.0)

    async def gen():
        for event in read_log(path):
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(1.0 if event["kind"] in {"PROPOSED", "WATCHING"} else 1.4)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/ledger")
def ledger() -> JSONResponse:
    conn = connect()
    rows = all_tests(conn)
    conn.close()
    return JSONResponse(rows)
