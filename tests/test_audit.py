"""Unit tests for audit.py HTML export."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit


def test_export_html_audit_contains_proof_sections(tmp_path):
    feed = [{'when': '2026-06-10T12:00:00', 'reason': 'large-file', 'src': 'C:\\a',
             'size': 1024, 'present': True, 'kind': 'file'}]
    custody = {'verified': 1, 'total': 1, 'missing': 0, 'bytes_in_custody': 1024, 'missing_items': []}
    summary = {'total_actions': 1, 'present': 1, 'missing': 0, 'bytes_moved': 1024,
               'reasons': Counter({'large-file': 1}), 'restore_events': 0}
    out = tmp_path / 'audit.html'
    audit.export_html_audit(feed, custody, summary, 100, out)
    html = out.read_text(encoding='utf-8')
    assert 'CUSTODY VERIFIED' in html
    assert 'Trust score' in html
    assert 'large-file' in html
    assert 'C:\\a' in html or 'C:&#92;a' in html or 'C:\\\\a' in html
