"""Tests for Disk Foresight (snapshot history + disk-full prediction)."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import foresight

GB = 1024 ** 3


def make_history(days_free_pairs, start=None):
    """[(day_offset, free_gb), ...] -> snapshot list."""
    start = start or datetime(2026, 6, 1, 12, 0, 0)
    return [{'ts': (start + timedelta(days=d)).isoformat(timespec='seconds'),
             'drive': 'C:\\', 'free': int(gb * GB), 'total': 500 * GB}
            for d, gb in days_free_pairs]


# ---------------------------------------------------------------------------
# trend
# ---------------------------------------------------------------------------
def test_trend_detects_steady_shrink():
    hist = make_history([(0, 100), (1, 98), (2, 96), (3, 94)])
    slope = foresight.trend_bytes_per_day(hist)
    assert slope is not None
    assert abs(slope - (-2 * GB)) < 0.01 * GB


def test_trend_needs_enough_points_and_span():
    assert foresight.trend_bytes_per_day(make_history([(0, 100), (1, 99)])) is None
    same_moment = make_history([(0, 100), (0, 100), (0, 100)])
    assert foresight.trend_bytes_per_day(same_moment) is None


def test_trend_ignores_corrupt_snapshots():
    hist = make_history([(0, 100), (1, 98), (2, 96), (3, 94)])
    hist.insert(1, {'ts': 'garbage', 'free': 'nan'})
    slope = foresight.trend_bytes_per_day(hist)
    assert slope is not None
    assert slope < 0


# ---------------------------------------------------------------------------
# forecast
# ---------------------------------------------------------------------------
def test_forecast_predicts_full_date():
    hist = make_history([(0, 100), (1, 98), (2, 96), (3, 94)])  # -2 GB/day, 94 free
    now = datetime(2026, 6, 4, 12, 0, 0)
    fc = foresight.forecast(hist, now=now)
    assert fc['free'] == 94 * GB
    assert abs(fc['days_until_full'] - 47) < 0.5
    assert fc['full_date'].year == 2026
    assert fc['full_date'] > now


def test_forecast_stable_disk_has_no_full_date():
    hist = make_history([(0, 100), (1, 100), (2, 100), (3, 100)])
    fc = foresight.forecast(hist)
    assert fc['days_until_full'] is None
    assert fc['full_date'] is None
    assert fc['slope_per_day'] is not None
    assert abs(fc['slope_per_day']) < 0.001 * GB


def test_forecast_growing_free_space_has_no_full_date():
    hist = make_history([(0, 90), (1, 95), (2, 100), (3, 105)])
    fc = foresight.forecast(hist)
    assert fc['days_until_full'] is None


def test_forecast_empty_history():
    fc = foresight.forecast([])
    assert fc == {'free': None, 'total': None, 'slope_per_day': None,
                  'days_until_full': None, 'full_date': None}


# ---------------------------------------------------------------------------
# days_bought
# ---------------------------------------------------------------------------
def test_days_bought():
    assert foresight.days_bought(10 * GB, -2 * GB) == 5
    assert foresight.days_bought(10 * GB, 2 * GB) is None
    assert foresight.days_bought(0, -2 * GB) is None
    assert foresight.days_bought(10 * GB, None) is None


# ---------------------------------------------------------------------------
# record_snapshot
# ---------------------------------------------------------------------------
def test_record_snapshot_writes_and_throttles(tmp_path):
    hist_path = tmp_path / 'disk_history.json'
    now = datetime(2026, 6, 9, 12, 0, 0)

    first = foresight.record_snapshot(history_path=hist_path, now=now)
    assert first['free'] > 0
    assert len(foresight.load_history(hist_path)) == 1

    # Within the throttle window: no new snapshot
    foresight.record_snapshot(history_path=hist_path, now=now + timedelta(hours=1))
    assert len(foresight.load_history(hist_path)) == 1

    # Past the window: appended
    foresight.record_snapshot(history_path=hist_path, now=now + timedelta(hours=7))
    assert len(foresight.load_history(hist_path)) == 2


def test_record_snapshot_caps_history(tmp_path):
    hist_path = tmp_path / 'disk_history.json'
    bloated = make_history([(i, 100) for i in range(foresight.MAX_SNAPSHOTS + 50)])
    hist_path.write_text(json.dumps(bloated))
    foresight.record_snapshot(history_path=hist_path,
                              now=datetime(2030, 1, 1, 12, 0, 0))
    assert len(foresight.load_history(hist_path)) == foresight.MAX_SNAPSHOTS


def test_load_history_tolerates_garbage(tmp_path):
    p = tmp_path / 'broken.json'
    p.write_text('{not json')
    assert foresight.load_history(p) == []
    p.write_text('{"a": 1}')
    assert foresight.load_history(p) == []


# ---------------------------------------------------------------------------
# health-score history
# ---------------------------------------------------------------------------
def test_record_health_appends_and_throttles(tmp_path):
    p = tmp_path / 'health.json'
    now = datetime(2026, 6, 9, 12, 0, 0)
    foresight.record_health(94, history_path=p, now=now)
    foresight.record_health(80, history_path=p, now=now + timedelta(hours=1))  # throttled
    foresight.record_health(72, history_path=p, now=now + timedelta(hours=7))
    history = foresight.load_health_history(p)
    assert [h['score'] for h in history] == [94, 72]
    assert all('ts' in h for h in history)


def test_record_health_caps_history(tmp_path):
    p = tmp_path / 'health.json'
    start = datetime(2026, 1, 1)
    bloated = [{'ts': (start + timedelta(hours=7 * i)).isoformat(timespec='seconds'),
                'score': 50} for i in range(foresight.MAX_SNAPSHOTS + 20)]
    p.write_text(json.dumps(bloated))
    foresight.record_health(99, history_path=p, now=datetime(2030, 1, 1))
    assert len(foresight.load_health_history(p)) == foresight.MAX_SNAPSHOTS
