"""
What this does: the ONLY file that talks to Gemini. Given a flagged slice, recent
metrics, and ledger recall, it asks the model for ONE test as structured JSON,
validates it into a Proposal, and (if the model is unreachable or returns garbage)
falls back to a deterministic local proposal — visibly degraded, never a crash.
What it must never do: decide if a test is allowed, compute any statistic, or read
the hidden truth. The model proposes; the rules and the scoreboard judge.
Where its numbers come from: Gemini for the idea; policy.yaml is enforced downstream.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from . import config  # noqa: F401 — importing loads .env so the key is present
from .models import Proposal, TestKind
from .watcher import Flag

_SCHEMA = {
    "type": "object",
    "properties": {
        "what_changed": {"type": "string"},
        "test_kind": {"type": "string", "enum": ["payment_method_order", "retry_timing"]},
        "traffic_share": {"type": "number"},
        "metric_to_watch": {"type": "string"},
        "why": {"type": "string"},
        "effect_to_detect_pp": {"type": "number"},
    },
    "required": ["what_changed", "test_kind", "traffic_share", "metric_to_watch", "why", "effect_to_detect_pp"],
}


def _prompt(flag: Flag, history: list[str]) -> str:
    hist = "\n".join(f"- {h}" for h in history) or "- (no prior tests yet)"
    return (
        "You optimise a merchant's checkout. Propose ONE small, safe test to run on the "
        "slice below. You do NOT decide whether it's allowed and you do NOT compute any "
        "statistic — a rules engine and a scoreboard do that.\n\n"
        f"Flagged slice: {flag.slice.label()}\n"
        f"Completion: usual {flag.baseline*100:.1f}%, recently {flag.recent*100:.1f}% "
        f"(down {flag.drop_pp:.1f} points)\n"
        f"History:\n{hist}\n\n"
        "Rules of thumb: allowed test kinds are payment_method_order or retry_timing; the "
        "traffic ceiling is about 10%; pick effect_to_detect_pp = the smallest change worth "
        "catching. Return only the JSON."
    )


def _call_gemini(prompt: str) -> dict | None:
    key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _SCHEMA},
    }).encode()
    try:
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"x-goog-api-key": key, "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception:
        return None


def _fallback(flag: Flag) -> Proposal:
    eff = max(4.0, round(flag.drop_pp)) if flag.drop_pp else 5.0
    return Proposal(
        what_changed=f"Show cards first for {flag.slice.label()}",
        test_kind=TestKind.payment_method_order, slice=flag.slice, traffic_share=0.10,
        metric_to_watch="checkout completion",
        why=f"completion here is {flag.drop_pp:.1f}pp below its usual level; the order was set long ago",
        effect_to_detect_pp=eff,
    )


def propose(flag: Flag, history: list[str]) -> tuple[Proposal, str, str | None]:
    """Returns (proposal, source, degraded_reason). source is 'gemini' or 'local'."""
    for _ in range(2):  # one retry, then give up to the fallback
        raw = _call_gemini(_prompt(flag, history))
        if raw is None:
            break
        try:
            raw.pop("slice", None)  # the fix targets the flagged slice; we set it, not the model
            p = Proposal(slice=flag.slice, **raw)
            return p, "gemini", None
        except Exception:
            continue
    return _fallback(flag), "local", "model unavailable — using local proposal"
