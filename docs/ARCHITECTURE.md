# Architecture

```
  event source                 (swappable)
  ├── simulator  ← guaranteed demo path
  └── Razorpay test-mode webhooks  ← proves it connects to real infra
            │
            ▼
  WATCHER      computes metrics, flags a slice that moved
            ▼
  REASONER     Gemini. Reads metrics + ledger. Returns a proposal.
            │      Never executes. Never computes a statistic.
            ▼
  RULES        Is this allowed? Plain Python + policy.yaml.
            ▼
  FEASIBILITY  Can this even be measured? Sample size + spending cap.
            ▼
  RUNNER       Splits traffic. Applies the setting. Watches the brake.
            ▼
  SCOREBOARD   Uplift, range, stop rules. Plain arithmetic, no AI.
            ▼
  LEDGER       SQLite. What happened, and what it cost.
            └──→ back into REASONER's context
```

## Two invariants
1. **The event log is the only thing the UI reads.** Every stage appends a line to
   `runs/<run_id>.jsonl`; the frontend renders that stream and nothing else. This
   gives byte-identical replay for free.
2. **The clock is injected.** `SimClock` runs at 10,000×; `WallClock` is real time,
   same `Protocol`. A correctly-sized 14-day test finishes in seconds on screen
   while every duration stays honest.

## Where each piece earns its place
| Piece | Job | Never does |
|---|---|---|
| Gemini | Suggests what's worth testing | Decide if it's allowed; compute any number |
| policy.yaml | Defines the boundaries | Change itself |
| Rules engine | Says yes or no | Guess |
| Feasibility | Says whether it's measurable + affordable | Ask the model |
| Scoreboard | Says whether it worked | Ask the model |
| SQLite ledger | What actually happened | Store opinions |
| Razorpay test mode | Proves real integration | Carry the demo |

## Files (backend)
`clock.py` · `eventlog.py` · `config.py` (policy loader) · `models.py` (shapes +
state machine) · `rules.py` · `feasibility.py` · `ledger.py` · `pipeline.py`
(authority spine) · `cli.py` (terminal renderer) · `sim/world.py` · `sim/truth.py`
(agent-forbidden). Runner, scoreboard, reasoner, watcher land in Checkpoints C–D.
