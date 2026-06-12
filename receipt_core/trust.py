"""Custody trust score computation (RECEIPT Core)."""


def trust_score(present, total):
    """0–100 custody trust score. Empty log → 100 (nothing broken yet)."""
    if total <= 0:
        return 100
    return int(round(100 * present / total))


def format_trust_score_display(verified_count, total_count, missing_count):
    """Proof/UI trust string — never perfect when any archive item is missing."""
    if total_count <= 0:
        return '100/100'
    raw_score = (verified_count / total_count) * 100
    if missing_count > 0:
        score = min(int(raw_score), 99)
    else:
        score = int(round(raw_score))
    return f'{score}/100'
