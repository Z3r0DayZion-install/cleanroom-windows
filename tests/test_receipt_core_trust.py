"""Direct unit tests for receipt_core.trust — parity with ledger.py shim."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ledger
from receipt_core import trust


def test_trust_score_matches_ledger_shim():
    assert trust.trust_score(2, 3) == ledger.trust_score(2, 3)
    assert trust.trust_score(0, 0) == ledger.trust_score(0, 0)
    assert trust.trust_score(2, 3) == 67
    assert trust.trust_score(0, 0) == 100


def test_format_trust_score_display_matches_ledger_shim():
    cases = (
        (1182, 1182, 0, '100/100'),
        (1181, 1182, 1, '99/100'),
        (0, 0, 0, '100/100'),
    )
    for verified, total, missing, expected in cases:
        assert trust.format_trust_score_display(verified, total, missing) == expected
        assert ledger.format_trust_score_display(verified, total, missing) == expected
