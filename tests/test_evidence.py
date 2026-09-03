"""The claims in the README, guarded. Kept small so the suite stays fast."""

from backend.evidence import cap_violations, cold_vs_experienced, false_positive_inflation


def test_peeking_inflates_false_positives_and_the_sequential_test_fixes_it():
    naive, seq = false_positive_inflation(trials=120)
    assert naive > 0.20, f"expected inflation from peeking, got {naive:.2f}"
    assert seq < 0.10, f"sequential test should stay near its alpha, got {seq:.2f}"
    assert naive > seq * 2


def test_cap_is_never_broken_across_seeds():
    tests, broken = cap_violations(seeds=10)
    assert tests > 0 and broken == 0


def test_experience_reaches_the_win_with_fewer_tests_and_less_loss():
    cw = cold_vs_experienced(seeds=10)
    assert cw["experienced_tests"] < cw["cold_tests"]
    assert cw["experienced_loss"] < cw["cold_loss"]
