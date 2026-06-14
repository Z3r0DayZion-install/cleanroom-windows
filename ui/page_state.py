"""Shared page state model — one truthful state per page at a time."""
from __future__ import annotations

IDLE_READY = 'idle_ready'
LOADING = 'loading'
EMPTY_DONE = 'empty_done'
RESULTS_READY = 'results_ready'
RECEIPT_READY = 'receipt_ready'
ERROR = 'error'


def cleaner_page_state(
    *,
    loading: bool = False,
    error: str = '',
    count: int = 0,
    checked: int = 0,
    scan_done: bool = False,
) -> tuple[str, str, str, str]:
    """Return (state, hero_title, hero_subtitle, footer_status)."""
    if loading:
        return (
            LOADING,
            'Scanning…',
            'Reviewing configured folders for candidates.',
            'Scanning configured folders…',
        )
    if error:
        short = error if len(error) < 80 else error[:77] + '…'
        return (
            ERROR,
            'Scan failed',
            short,
            f'Scan failed: {short}',
        )
    if count > 0 and checked > 0:
        return (
            RECEIPT_READY,
            'Receipt ready',
            f'{count} candidate(s) · {checked} checked · preview receipt before archive.',
            f'Receipt ready — {count} candidate(s), {checked} checked.',
        )
    if count > 0:
        return (
            RESULTS_READY,
            'Candidates found',
            f'{count} candidate(s) — check items, then preview receipt.',
            f'Scan complete — {count} candidate(s) found.',
        )
    if scan_done:
        return (
            EMPTY_DONE,
            'Scan complete',
            'No cleanup candidates found in configured folders.',
            'Scan complete — no candidates found.',
        )
    return (
        IDLE_READY,
        'Ready to scan',
        'Scan configured folders — preview receipt before any archive.',
        'Ready to scan.',
    )


def home_page_state(
    *,
    loading: bool = False,
    error: str = '',
    count: int = 0,
    checked: int = 0,
    scan_done: bool = False,
    custody_missing: int = 0,
) -> tuple[str, str, str, str]:
    """Return (state, hero_title, hero_subtitle, status_line)."""
    if loading:
        return (
            LOADING,
            'Scanning…',
            'Reviewing configured folders for cleanup candidates.',
            'Scanning configured folders…',
        )
    if error:
        short = error if len(error) < 80 else error[:77] + '…'
        return ERROR, 'Scan failed', short, f'Scan failed: {short}'
    if count > 0 and checked > 0:
        return (
            RECEIPT_READY,
            'Receipt ready',
            f'{count} candidate(s) ready — preview receipt, then archive.',
            f'Receipt ready — {count} candidate(s), {checked} checked.',
        )
    if count > 0:
        return (
            RESULTS_READY,
            'Candidates found',
            f'{count} candidate(s) found — review on Cleaner before archive.',
            f'{count} candidate(s) awaiting review.',
        )
    if scan_done:
        return (
            EMPTY_DONE,
            'Scan complete',
            'No cleanup candidates in configured folders.',
            'Scan complete — no candidates found.',
        )
    if custody_missing:
        return (
            RESULTS_READY,
            'Custody review needed',
            f'{custody_missing} archived artifact(s) missing on disk.',
            f'{custody_missing} custody gap(s) — review Activity.',
        )
    return (
        IDLE_READY,
        'Ready to scan',
        'Archive-first cleanup with receipts.',
        'Ready to scan.',
    )
