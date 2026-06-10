#!/usr/bin/env python3
"""Time Machine: group every archive-first action by day and roll whole days
back. Works over the cleanup log (cleaner moves + uninstall leftovers).
Pure functions; the GUI supplies the restore callable."""
import os
from collections import Counter
from datetime import datetime


def day_of(ts):
    """'YYYY-MM-DD' from an ISO timestamp, else None."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts)).strftime('%Y-%m-%d')
    except Exception:
        return str(ts)[:10] if len(str(ts)) >= 10 else None


def build_timeline(actions):
    """Group log actions into day buckets, newest first.

    Each bucket: {'date', 'count', 'bytes', 'restorable', 'reasons': Counter,
                  'entries': [(src, dest, ts, raw), ...]}
    Restore records (action == 'restore') are skipped — they are bookkeeping,
    not state that can be rolled back.
    """
    days = {}
    for raw in actions:
        if not isinstance(raw, dict) or raw.get('action') == 'restore':
            continue
        src = raw.get('src') or raw.get('src_path') or raw.get('source') or raw.get('original')
        dest = (raw.get('dest') or raw.get('dest_path') or raw.get('target')
                or raw.get('archive') or raw.get('archived_path'))
        if not src or not dest:
            continue
        ts = raw.get('timestamp') or raw.get('time') or raw.get('when')
        date = day_of(ts) or 'unknown'
        bucket = days.setdefault(date, {
            'date': date, 'count': 0, 'bytes': 0, 'restorable': 0,
            'reasons': Counter(), 'entries': [],
        })
        bucket['count'] += 1
        try:
            bucket['bytes'] += int(raw.get('size') or 0)
        except (TypeError, ValueError):
            pass
        bucket['reasons'][raw.get('reason') or 'other'] += 1
        if os.path.exists(dest):
            bucket['restorable'] += 1
        bucket['entries'].append((src, dest, ts, raw))
    return sorted(days.values(), key=lambda b: b['date'], reverse=True)


def rollback_day(bucket, restore_fn):
    """Restore every still-archived entry of a day bucket.

    restore_fn(src, dest) -> (ok, msg). Returns (restored, skipped, failed,
    messages)."""
    restored = skipped = failed = 0
    messages = []
    for src, dest, ts, raw in bucket['entries']:
        if not os.path.exists(dest):
            skipped += 1
            continue
        try:
            ok, msg = restore_fn(src, dest)
        except Exception as e:
            ok, msg = False, str(e)
        if ok:
            restored += 1
        else:
            failed += 1
            messages.append(msg)
    return restored, skipped, failed, messages
