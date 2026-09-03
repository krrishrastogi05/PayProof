"""
What this does: append-only event log, one JSON line per stage, to
runs/<run_id>.jsonl. The UI is a pure function of this file, which is what gives
us byte-identical replay for free.
What it must never do: read from or depend on the UI; mutate past lines.
Where its numbers come from: sim/real time come from the injected Clock.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Iterator

from .clock import Clock

RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


class EventLog:
    def __init__(self, run_id: str, clock: Clock, runs_dir: Path = RUNS_DIR) -> None:
        runs_dir.mkdir(parents=True, exist_ok=True)
        self.path = runs_dir / f"{run_id}.jsonl"
        self._clock = clock
        self._seq = 0
        self._fh = self.path.open("a", encoding="utf-8")

    def append(self, kind: str, **fields: Any) -> dict[str, Any]:
        """Write one line. `kind` is the card type the UI will render."""
        self._seq += 1
        line = {
            "seq": self._seq,
            "real_ts": round(time.time(), 3),
            "sim_ts": round(self._clock.now(), 1),
            "kind": kind,
            **fields,
        }
        self._fh.write(json.dumps(line, default=str) + "\n")
        self._fh.flush()
        return line

    def close(self) -> None:
        self._fh.close()


def read_log(path: str | Path) -> Iterator[dict[str, Any]]:
    """Replay source: yield each recorded line in order."""
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if raw:
                yield json.loads(raw)
