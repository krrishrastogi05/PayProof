# Limitations

Stated plainly, because hiding these is the one thing that could sink the submission.

## Execution is simulated
Thaw does not write to a live merchant account. It reads, and it writes in **test
mode only**. The heavy lifting — traffic, outcomes, revenue — comes from a
deterministic simulator (`backend/sim/`). This is deliberate: we know the right
answers, so we can *check* whether the agent found them.

## Effect sizes are inflated, on purpose
Real payment-setting effects are **1–3 percentage points**. We seeded a **7-point**
win into one slice so the whole loop is visible inside a five-minute video. This is
disclosed, not hidden — and it cuts both ways:

- At realistic effect sizes and this traffic volume, the **feasibility gate
  correctly refuses to run** — the sample size doesn't arrive inside the time
  limit. We show that too (the `TOO SMALL TO MEASURE` beat is a real 2-point test).
- So the honest reading is: the *machinery* is real; the *effect* is amplified for
  legibility. On live traffic you'd run fewer, longer, larger tests — the gate is
  what tells you which ones are worth starting at all.

## Ground truth is isolated, and tested
The simulator's hidden effects live in `backend/sim/truth.py`. No agent-side module
may import it; `tests/test_truth_isolation.py` enforces this. If it could see the
answers, "the AI found the win" would mean nothing.

## What would have to be true to run this live
- A real assignment hook in the Checkout SDK for `config.display.sequence`, keyed by
  a stable session id, with a guaranteed revert path.
- A metrics source with low enough latency that the brake can act within its window.
- Legal/compliance sign-off that Layer-1 boundaries in `policy.yaml` (never change an
  amount, never skip auth, always keep a control) match the merchant's obligations.
- Longer horizons: at 1–3pp, tests run for weeks, not seconds. The clock speed-up in
  the demo is honest about durations — it only compresses wall-clock, never the math.

## Not built (by choice — see the non-goals)
No multi-merchant support, no login, no settings UI (the policy file is edited by
hand, and that's the point), no more than two kinds of test, no vector DB.
