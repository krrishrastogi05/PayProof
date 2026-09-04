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


@app.post("/policy/set")
async def policy_set(body: dict) -> JSONResponse:
    """Tune a policy limit at runtime — the CLI standing in for a human editing
    policy.yaml. Kept in memory; the committed file is never touched."""
    from .config import clear_overrides, set_override, tunables
    key, value = body.get("key", ""), body.get("value", "")
    if key == "reset":
        clear_overrides()
        return JSONResponse({"ok": True, "message": "policy reset to file defaults"})
    try:
        return JSONResponse({"ok": True, "message": set_override(str(key), str(value))})
    except (KeyError, ValueError) as e:
        return JSONResponse({"ok": False, "message": str(e), "tunable": tunables()}, status_code=400)


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
    """What the agent has learned — the ledger as a memory graph.
    Each concluded decision is a claim; we phrase it so the record is honest
    about what didn't work, not just the wins."""
    conn = connect()
    tests = all_tests(conn)
    head = {t["id"]: t.get("headline", "") for t in tests}
    decisions = [dict(r) for r in conn.execute(
        "SELECT test_id, decision, uplift, ci_low, ci_high, reason FROM decisions ORDER BY rowid DESC")]
    conn.close()

    def _subject(h: str) -> str:  # keep the headline readable, family-agnostic
        return h.replace("Show cards first for ", "Cards-first · ").strip() or h

    seen, learns = set(), []
    for d in decisions:
        h = head.get(d["test_id"], "")
        subject = _subject(h)
        if subject in seen:
            continue
        seen.add(subject)
        pp, verb = round((d["uplift"] or 0) * 100, 1), d["decision"]
        # verb carries WINS / HURT / wash so the graph tones the card by outcome
        if verb == "FOUND_WINNER":
            claim = f"WINS +{pp}pp · {subject} — kept {d['reason']}"
        elif verb == "FOUND_HARMFUL":
            claim = f"HURT {pp}pp · {subject} — reverted, won't repeat"
        else:
            claim = f"wash · {subject} — no measurable lift {d['reason']}"
        learns.append({"test_id": d["test_id"], "claim": claim})

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
