#!/usr/bin/env python3
"""Proof of work: measured evidence that Cleanroom actually did something.

Most optimizers print a made-up number and call it a day. This module
produces evidence that can be independently checked:

- disk free space is measured from the OS (shutil.disk_usage) before and
  after an operation — never estimated from summed file sizes
- a "custody check" verifies that every archived artifact (moved file or
  exported .reg) actually exists on disk right now, so the reversibility
  promise is checkable at any time, not just claimed
"""
import shutil
from pathlib import Path

REG_PREFIX = 'REGISTRY::'


def disk_free(path='C:\\'):
    """OS-measured free bytes on the volume containing path (0 on failure)."""
    try:
        return shutil.disk_usage(str(path)).free
    except Exception:
        return 0


def volume_of(path):
    """Drive anchor of a path ('C:\\'); safe fallback for relative paths."""
    try:
        anchor = Path(path).resolve().anchor
        return anchor or 'C:\\'
    except Exception:
        return 'C:\\'


def verify_entries(entries):
    """Custody check over cleanup-log entries: does each archived artifact
    (file, folder, or .reg export) still exist where the log says it is?

    Returns {'total', 'verified', 'missing', 'missing_items', 'bytes_in_custody'}.
    """
    total = verified = 0
    missing_items = []
    bytes_in_custody = 0
    for e in entries:
        dest = e.get('dest')
        if not dest:
            continue
        total += 1
        p = Path(dest)
        if p.exists():
            verified += 1
            try:
                if p.is_file():
                    bytes_in_custody += p.stat().st_size
                else:
                    bytes_in_custody += sum(f.stat().st_size
                                            for f in p.rglob('*') if f.is_file())
            except Exception:
                pass
        else:
            missing_items.append(str(e.get('src') or dest))
    return {
        'total': total,
        'verified': verified,
        'missing': total - verified,
        'missing_items': missing_items,
        'bytes_in_custody': bytes_in_custody,
    }


def build_proof(before_free, after_free, entries):
    """Assemble the proof record for a completed operation."""
    claimed = 0
    for e in entries:
        try:
            claimed += int(e.get('size') or 0)
        except (TypeError, ValueError):
            pass
    return {
        'before_free': before_free,
        'after_free': after_free,
        'measured_delta': after_free - before_free,
        'claimed_bytes': claimed,
        'custody': verify_entries(entries),
    }


def _human(n):
    sign = '-' if n < 0 else ''
    n = abs(n)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{sign}{n:.1f}{unit}'
        n /= 1024
    return f'{sign}{n:.1f}PB'


def format_proof(proof):
    """Receipt section: measured numbers with an honest reading of them."""
    custody = proof['custody']
    lines = [
        '  PROOF (measured by the OS, not estimated):',
        f'    Free space before:  {_human(proof["before_free"])}',
        f'    Free space after:   {_human(proof["after_free"])}',
        f'    Measured change:    {_human(proof["measured_delta"])}',
    ]
    moved = proof['claimed_bytes']
    if proof['measured_delta'] < moved // 2:
        lines.append(f'    ({_human(moved)} was MOVED to the archive, not deleted —')
        lines.append('     free space changes when you prune the archive.)')
    lines.append(f'    Custody check:      {custody["verified"]}/{custody["total"]} '
                 'archived item(s) verified present')
    if custody['missing']:
        lines.append(f'    WARNING: {custody["missing"]} item(s) NOT found in the archive!')
    return lines
