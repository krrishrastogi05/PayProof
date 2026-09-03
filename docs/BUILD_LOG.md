# Build log — real dead ends, dated

The buildathon judges failure recovery explicitly. These are actual things that
broke and how they were fixed, newest first.

## 2026-09-03 — Checkpoint A + B

**Built:** clock abstraction, event-log writer, SQLite ledger schema, the
simulator with hidden truths, `policy.yaml` + rules engine, the feasibility gate
(sample size + spending cap), the lifecycle state machine, and a terminal card
stream. 15 tests green.

**Broke: feasibility made even the good test look infeasible.**
First cut of `days_to_run` divided the slice's arrival by `traffic_share` (10%),
so the 7-point test needed ~18 days and got declined — which contradicts the demo
(that test is supposed to *run*). Root cause: I modelled traffic_share as a divisor
of the slice when it's really a separate *ceiling* on how much of total traffic the
experiment may touch. Fix: enroll the whole flagged slice 50/50 and check
`traffic_share` in the rules engine instead. That change is also what makes the
PRD's beat-4 arithmetic reproduce exactly (412 sessions/day → ~38 days).

**Broke: the truth-isolation test failed on its own docstring.**
`test_reasoner_cannot_see_ground_truth` did `assert "truth" not in source`, which
tripped on the *word* "truth" in `feasibility.py`'s "must never look at the hidden
truth" comment. Fix: scan only `import`/`from` lines. The test now catches real
imports, not prose.

**Broke: Windows console crashed printing the card stream.**
`UnicodeEncodeError: 'charmap' codec can't encode '●'` — the cp1252 default
console can't render `●`. Fix: `sys.stdout.reconfigure(encoding="utf-8")` at the top
of the CLI. (A reminder that "works on my machine" hides an encoding assumption.)

**Broke: re-running the demo duplicated every card.**
The event log opens in append mode (correct for a single live run), but re-running
into the same `run_id` stacked a second run on top, so `replay` showed doubles. Fix:
truncate `runs/<run_id>.jsonl` at the start of a run, so a run is written once and
replays byte-for-byte.

**Decision:** reused the buildathon's already-configured service keys (Gemini,
Razorpay test mode, Supermemory, Supabase) via a shared `.env` rather than standing
up new credentials — keeps setup at zero and the demo path identical.
