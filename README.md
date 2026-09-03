# Thaw

**Every merchant's payment settings are a frozen guess. Thaw un-freezes them — with a spending cap, an emergency brake, and an honest record of what didn't work.**

When a merchant integrates payments, someone picks the settings once — which method shows first, how retries are timed — and then nobody revisits them. The business changes; the settings don't. Thaw watches the payment data, notices when a slice moved, proposes a small test, checks whether it's *allowed* and whether it can even be *measured*, runs it on a tiny slice of traffic under a hard rupee cap, and either keeps the change or reverts it. Every result goes in a ledger, so the next test is smarter than the last.

Razorpay AI Buildathon — **Open Track**.

## Why it's not a "recovery agent"

Razorpay shipped Agent Studio; Optimizer already picks the gateway *behind* the payment. Thaw works on what the customer *sees* at checkout (`config.display.sequence` in the Checkout SDK). Adyen ships tests on that layer, but a human starts and stops each one. See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

The safety model is borrowed from **clinical trials, not canary releases** — because a failed checkout is a lost order, and rolling back isn't free. Money at risk is capped in rupees *before* a test starts; stopping for harm needs far less evidence than promoting a winner; a separate monitor outranks the agent.

## What runs today (Checkpoints A–B)

The deterministic spine and the two hardest-to-fake beats:

- **Rules engine** (`backend/rules.py`) — reads `policy.yaml`, allows or blocks with a reason. Highest test coverage in the repo.
- **Feasibility gate** (`backend/feasibility.py`) — sample-size arithmetic + the spending cap, computed *before* anything runs. Declines tests it can't measure.
- **The simulator** (`backend/sim/`) with hidden ground truth the agent's code cannot import (enforced by a test).
- **Event log + ledger** — every stage appends one line; the UI is a pure function of that stream (free replay).

```bash
# from thaw/
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
python -m pytest -v              # reads like a spec
python -m backend.cli           # renders the card stream: BLOCKED, TOO SMALL, CAP SET…
python -m backend.cli replay runs/run_042.jsonl
```

Sample output — the agent asks for 25% traffic (**blocked**, ceiling is 10%), comes back at 10% (**cap set: ₹18,862**), then proposes a test on a slice that gets 412 sessions/day and **declines it itself**: ~7,900 per group is 38 days, past the 14-day limit.

## Roadmap to the full demo

- **C** — runner (hashed assignment, layers), scoreboard (sequential test, lopsided thresholds, split check), the brake + realized-loss accounting.
- **D** — Gemini reasoner (structured output only; never computes a number), ledger recall, degraded fallback. Reuses the buildathon's configured keys.
- **E** — Next.js page, SSE card stream, money meter, replay mode.
- **F** — the honesty run, cold-vs-experienced over 20 seeds, cap-violation count, prior-art table.

## Submission mapping

| Requirement | Where |
|---|---|
| Public repo, clean & runnable | this repo; `pytest -v` green |
| 5-min pitch video | the 8 beats in the build plan |
| Architecture docs | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) |
| What broke & how we recovered | [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md) |
| Honest about limits | [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) |

All figures are **simulated**. Test mode only. No real money, ever.
