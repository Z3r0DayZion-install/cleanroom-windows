import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / 'main.py'
CFG = ROOT / 'cleanup_config.yaml'


def test_main_json_output():
    # Run main.py in JSON dry-run mode
    p = subprocess.run([sys.executable, str(MAIN), '--config', str(CFG), '--json'], capture_output=True, text=True, check=True)
    data = json.loads(p.stdout)
    assert 'candidates' in data
    assert isinstance(data['candidates'], list)
    # Expect at least one candidate from previous runs
    assert data['count'] == len(data['candidates'])
    assert data['total_bytes'] >= 0


def _import_main():
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    import main as m
    return m


def test_scan_candidates_respects_exclude_patterns(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    include_file = test_root / 'keep.txt'
    exclude_file = test_root / 'skip.txt'
    include_file.write_text('keep')
    exclude_file.write_text('skip')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': ['*skip.txt'],
        'whitelist': [],
    }
    candidates = m.scan_candidates(cfg)
    assert any('keep.txt' in c['path'] for c in candidates)
    assert not any('skip.txt' in c['path'] for c in candidates)


def test_scan_candidates_respects_whitelist(tmp_path, monkeypatch):
    m = _import_main()
    test_root = tmp_path / 'testfolder'
    test_root.mkdir()
    kept_file = test_root / 'keep.txt'
    white_file = test_root / 'whitelist.txt'
    kept_file.write_text('keep')
    white_file.write_text('white')
    cfg = {
        'paths': [str(test_root)],
        'age_days': {'temp': -1, 'installers': -1},
        'size_threshold_mb': 0,
        'extensions_archive': ['.txt'],
        'exclude_patterns': [],
        'whitelist': ['*whitelist.txt'],
    }
    candidates = m.scan_candidates(cfg)
    assert any('keep.txt' in c['path'] for c in candidates)
    assert not any('whitelist.txt' in c['path'] for c in candidates)
