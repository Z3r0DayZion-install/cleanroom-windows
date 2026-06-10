#!/usr/bin/env python3
"""Disk Foresight: predict when the disk will be full.

Cleanroom records a free-space snapshot every time it runs. A least-squares
trend over those snapshots estimates how fast the disk is filling, which date
it runs out, and how many days a cleanup would buy. All math is pure and
unit-testable; only record_snapshot touches the filesystem.
"""
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import brand

HISTORY_PATH = brand.user_data_dir() / 'disk_history.json'
MAX_SNAPSHOTS = 1000


def load_history(history_path=None):
    path = Path(history_path or HISTORY_PATH)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def record_snapshot(drive=None, history_path=None, min_interval_hours=6, now=None):
    """Append a free-space snapshot unless one was taken recently.
    Returns the snapshot list's last entry."""
    drive = drive or os.path.splitdrive(str(Path.home()))[0] + '\\'
    path = Path(history_path or HISTORY_PATH)
    now = now or datetime.now()
    history = load_history(path)

    if history:
        try:
            last = datetime.fromisoformat(history[-1]['ts'])
            if (now - last) < timedelta(hours=min_interval_hours):
                return history[-1]
        except Exception:
            pass

    usage = shutil.disk_usage(drive)
    entry = {'ts': now.isoformat(timespec='seconds'),
             'drive': drive, 'free': usage.free, 'total': usage.total}
    history.append(entry)
    history = history[-MAX_SNAPSHOTS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding='utf-8')
    return entry


def _points(history):
    """(days_since_first, free_bytes) pairs from valid snapshots."""
    pts = []
    t0 = None
    for snap in history:
        try:
            ts = datetime.fromisoformat(snap['ts'])
            free = int(snap['free'])
        except Exception:
            continue
        if t0 is None:
            t0 = ts
        pts.append(((ts - t0).total_seconds() / 86400.0, free))
    return pts


def trend_bytes_per_day(history):
    """Least-squares slope of free space (bytes/day). None when there isn't
    at least ~half a day of history across 3+ snapshots."""
    pts = _points(history)
    if len(pts) < 3:
        return None
    span = pts[-1][0] - pts[0][0]
    if span < 0.5:
        return None
    n = len(pts)
    mean_x = sum(x for x, _ in pts) / n
    mean_y = sum(y for _, y in pts) / n
    denom = sum((x - mean_x) ** 2 for x, _ in pts)
    if denom == 0:
        return None
    return sum((x - mean_x) * (y - mean_y) for x, y in pts) / denom


def forecast(history, now=None):
    """Summarize the trend.

    Returns dict with:
      free, total       latest snapshot bytes (None without history)
      slope_per_day     bytes/day change in free space (negative = filling up)
      days_until_full   None unless the disk is shrinking
      full_date         datetime when free space hits zero at this rate
    """
    now = now or datetime.now()
    result = {'free': None, 'total': None, 'slope_per_day': None,
              'days_until_full': None, 'full_date': None}
    if not history:
        return result
    last = history[-1]
    result['free'] = int(last.get('free') or 0)
    result['total'] = int(last.get('total') or 0)
    slope = trend_bytes_per_day(history)
    result['slope_per_day'] = slope
    if slope is not None and slope < 0 and result['free'] > 0:
        days = result['free'] / -slope
        result['days_until_full'] = days
        result['full_date'] = now + timedelta(days=days)
    return result


def days_bought(reclaimable_bytes, slope_per_day):
    """How many extra days a cleanup buys at the current burn rate."""
    if not reclaimable_bytes or slope_per_day is None or slope_per_day >= 0:
        return None
    return reclaimable_bytes / -slope_per_day


# ---------------------------------------------------------------------------
# Health-score history (same snapshot pattern as disk history)
# ---------------------------------------------------------------------------
HEALTH_PATH = brand.user_data_dir() / 'health_history.json'


def load_health_history(history_path=None):
    path = Path(history_path or HEALTH_PATH)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def record_health(score, history_path=None, min_interval_hours=6, now=None):
    """Append a health-score snapshot unless one was taken recently."""
    path = Path(history_path or HEALTH_PATH)
    now = now or datetime.now()
    history = load_health_history(path)
    if history:
        try:
            last = datetime.fromisoformat(history[-1]['ts'])
            if (now - last) < timedelta(hours=min_interval_hours):
                return history[-1]
        except Exception:
            pass
    entry = {'ts': now.isoformat(timespec='seconds'), 'score': int(score)}
    history.append(entry)
    history = history[-MAX_SNAPSHOTS:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding='utf-8')
    return entry
