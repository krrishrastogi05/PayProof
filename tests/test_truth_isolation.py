"""
The claim that makes the whole project honest: the agent's reasoning code cannot
see the simulator's ground truth. If it could, "the AI found the answer" would mean
nothing. Mention this test on camera.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"

# Every module that reasons about what to test. None may reach the hidden truth.
AGENT_MODULES = ["reasoner.py", "watcher.py", "rules.py", "feasibility.py", "scoreboard.py"]


def test_reasoner_cannot_see_ground_truth():
    for name in AGENT_MODULES:
        f = BACKEND / name
        if not f.exists():
            continue  # not built yet; enforced the moment it is
        for line in f.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            imports_truth = s.startswith(("import ", "from ")) and "truth" in s
            assert not imports_truth, f"{name} imports the hidden truth — it must not"


def test_importing_the_agent_side_does_not_load_truth():
    for mod in ("backend.rules", "backend.feasibility"):
        __import__(mod)
    assert "backend.sim.truth" not in sys.modules, "an agent module pulled in ground truth"
