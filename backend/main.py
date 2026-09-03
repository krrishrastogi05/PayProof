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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from .cli import run_demo, run_live
from .config import POLICY_PATH, load_policy
from .eventlog import read_log
from .ledger import all_tests, connect

app = FastAPI(title="Thaw")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
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


@app.get("/policy")
def policy() -> JSONResponse:
    p = load_policy()
    return JSONResponse({"yaml": POLICY_PATH.read_text(encoding="utf-8"), "parsed": p.model_dump()})


@app.get("/dataset")
def dataset() -> JSONResponse:
    """The observable world the merchant sees — slices, traffic, order sizes."""
    from .sim.world import AVG_ORDER_INR, BAND_SHARE, CTYPE_SHARE, DEVICE_SHARE, TOTAL_PER_DAY, arrival_per_day
    from .watcher import _BASELINE, _WATCHED
    slices = [{"slice": s.label(), "device": s.device.value, "customer_type": s.customer_type.value,
               "order_band": s.order_band, "arrival_per_day": arrival_per_day(s),
               "avg_order_inr": AVG_ORDER_INR.get(s.order_band, 1500)} for s in _WATCHED]
    return JSONResponse({"total_per_day": TOTAL_PER_DAY, "baseline_completion": _BASELINE,
                         "device_share": DEVICE_SHARE, "customer_share": CTYPE_SHARE,
                         "order_band_share": BAND_SHARE, "watched_slices": slices})


@app.get("/memory")
def memory() -> JSONResponse:
    """What the agent has learned — the ledger as a memory graph."""
    conn = connect()
    tests = all_tests(conn)
    learns = [dict(r) for r in conn.execute("SELECT test_id, claim FROM learnings ORDER BY id DESC")]
    decisions = [dict(r) for r in conn.execute("SELECT test_id, decision, uplift, ci_low, ci_high, reason FROM decisions")]
    conn.close()
    return JSONResponse({"tests": tests, "learnings": learns, "decisions": decisions})


_EVIDENCE: dict | None = None


@app.get("/evidence")
async def evidence() -> JSONResponse:
    """The measured claims, computed once and cached. Real numbers, not typed in."""
    global _EVIDENCE
    if _EVIDENCE is None:
        from .evidence import cap_violations, cold_vs_experienced, false_positive_inflation

        def _compute():
            naive, seq = false_positive_inflation(trials=200)
            tests, broken = cap_violations(seeds=20)
            cw = cold_vs_experienced(seeds=20)
            return {"fp_naive": round(naive * 100, 1), "fp_sequential": round(seq * 100, 1),
                    "cap_tests": tests, "cap_broken": broken, **cw}

        _EVIDENCE = await asyncio.to_thread(_compute)
    return JSONResponse(_EVIDENCE)
