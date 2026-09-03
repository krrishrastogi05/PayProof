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

from .cli import run_demo, run_live
from .eventlog import read_log
from .ledger import all_tests, connect

app = FastAPI(title="Thaw")
FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(FRONTEND.read_text(encoding="utf-8"))


@app.get("/stream")
async def stream(seed: int = 42, live: int = 0):
    """Generate a run (curated replay, or live via Gemini), then stream its cards.
    The live run really calls Gemini; the curated replay is the guaranteed demo."""
    path = await asyncio.to_thread(run_live if live else run_demo, seed, 10_000.0)

    fast = {"RUNNING"}
    weighty = {"BRAKE_PULLED", "KEPT", "NO_DIFFERENCE", "REVERTED", "LEARNED"}

    async def gen():
        for event in read_log(path):
            yield f"data: {json.dumps(event)}\n\n"
            kind = event["kind"]
            await asyncio.sleep(0.3 if kind in fast else 1.35 if kind in weighty else 1.05)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/ledger")
def ledger() -> JSONResponse:
    conn = connect()
    rows = all_tests(conn)
    conn.close()
    return JSONResponse(rows)
