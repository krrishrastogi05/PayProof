# Thaw

**Every merchant's payment settings are a frozen guess. Thaw un-freezes them — with a spending cap, an emergency brake, and an honest record of what didn't work.**

When a merchant integrates payments, someone picks the settings once — which method shows first, how retries are timed — and then nobody revisits them. The business changes; the settings don't. Thaw watches the payment data, notices when a slice moved, proposes a small test, checks whether it's *allowed* and whether it can even be *measured*, runs it on a tiny slice of traffic under a hard rupee cap, and either keeps the change or reverts it. Every result goes in a ledger, so the next test is smarter than the last.

Razorpay AI Buildathon — **Open Track**.

## Why it's not a "recovery agent"

Razorpay shipped Agent Studio; Optimizer already picks the gateway *behind* the payment. Thaw works on what the customer *sees* at checkout (`config.display.sequence` in the Checkout SDK). Adyen ships tests on that layer, but a human starts and stops each one. See [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md).

The safety model is borrowed from **clinical trials, not canary releases** — because a failed checkout is a lost order, and rolling back isn't free. Money at risk is capped in rupees *before* a test starts; stopping for harm needs far less evidence than promoting a winner; a separate monitor outranks the agent.

## What runs today

The whole pipeline, end to end:

- **Watcher** (`backend/watcher.py`) — flags a slice whose completion has slipped.
- **Reasoner** (`backend/reasoner.py`) — the only file that talks to **Gemini**;
  reads the flagged slice + ledger recall, returns one structured proposal, and
  falls back to a local proposal (visibly degraded) if the model is unreachable.
- **Rules engine** (`backend/rules.py`) — reads `policy.yaml`, allows or blocks with a reason. Highest test coverage in the repo.
- **Feasibility gate** (`backend/feasibility.py`) — sample-size arithmetic + the spending cap, computed *before* anything runs. Declines tests it can't measure.
- **Runner + scoreboard** (`backend/runner.py`, `scoreboard.py`) — hashed session
  assignment, a sequential (mSPRT) test with lopsided promote/harm thresholds, the
  split check, realized-loss accounting, and **the brake** (the cap is never exceeded).
- **The simulator** (`backend/sim/`) with hidden ground truth the agent's code cannot import (enforced by a test).
- **Event log + ledger + web UI** — every stage appends one line; the page is a pure
  function of that stream (free replay).

```bash
# from thaw/
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt
python -m pytest -v              # reads like a spec
python -m backend.cli           # renders the card stream: BLOCKED, TOO SMALL, CAP SET…
python -m backend.cli replay runs/run_042.jsonl
```

Sample output — the agent asks for 25% traffic (**blocked**, ceiling is 10%), comes back at 10% (**cap set: ₹18,862**), then proposes a test on a slice that gets 412 sessions/day and **declines it itself**: ~7,900 per group is 38 days, past the 14-day limit.

## Evidence (measured, not claimed)

Run it yourself: `python -m backend.evidence`.

- **Peeking inflates false positives; the sequential test fixes it.** With both
  options secretly identical and a look after every batch, naive re-checking of a
  fixed-horizon p-value declares a winner on **38.8%** of runs; Thaw's sequential
  (mSPRT) test, **2.5%**.
- **The spending cap is never exceeded.** Across **80 tests over 20 seeds**,
  `cap_broken = 0`.
- **Experience pays.** Reading the ledger, the agent reaches the real win in
  **1.0 test and ₹0 lost**, vs **3.0 tests and ₹2,878 lost** cold — it skips the
  slices it already learned are harmful or a wash.

## Live vs replay

- **Replay** (`Start run`, or `python -m backend.cli`) — the curated, deterministic
  demo. Effects are inflated so all six end-states fire in five minutes.
- **Live** (the *Live · Gemini* toggle, or `python -m backend.cli live`) — really
  calls Gemini for each flagged slice. At realistic effect sizes the model's own
  proposals are **declined by the feasibility gate** (a 1-point change needs ~90
  days at this traffic) — which is the honest point, shown, not hidden.

## Status

Checkpoints **A–D and F done, E working** (web UI). Beats 1–8 are demonstrable.
Remaining polish: porting the vanilla page to the Next.js named in the spec, and
the optional Razorpay test-mode event source.

## Submission mapping

| Requirement | Where |
|---|---|
| Public repo, clean & runnable | this repo; `pytest -v` green |
| 5-min pitch video | the 8 beats in the build plan |
| Architecture docs | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/PRIOR_ART.md`](docs/PRIOR_ART.md) |
| What broke & how we recovered | [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md) |
| Honest about limits | [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) |

All figures are **simulated**. Test mode only. No real money, ever.
