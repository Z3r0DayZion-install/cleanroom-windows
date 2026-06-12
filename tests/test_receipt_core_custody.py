"""Direct unit tests for receipt_core.custody — parity with proof.py shim."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import proof
from receipt_core import custody


def _entry(dest, size=10, src=None, reason='large-file'):
    return {'src': src or f'C:\\junk\\{Path(dest).name}', 'dest': str(dest),
            'reason': reason, 'size': size, 'when': '2026-06-10T12:00:00'}


def test_verify_entries_matches_proof_shim(tmp_path):
    present = tmp_path / 'a.bin'
    present.write_bytes(b'x' * 64)
    folder = tmp_path / 'leftover_dir'
    (folder / 'sub').mkdir(parents=True)
    (folder / 'sub' / 'f.txt').write_bytes(b'y' * 32)
    entries = [
        _entry(present, size=64),
        _entry(folder, size=32),
        _entry(tmp_path / 'gone.bin', size=99),
    ]
    core = custody.verify_entries(entries)
    shim = proof.verify_entries(entries)
    assert core == shim


def test_build_proof_matches_proof_shim(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 100)
    entries = [_entry(f, size=100)]
    core = custody.build_proof(1000, 1300, entries)
    shim = proof.build_proof(1000, 1300, entries)
    assert core == shim


def test_format_proof_matches_proof_shim(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 100)
    prf = custody.build_proof(10_000_000, 10_000_100, [_entry(f, size=1024 * 1024)])
    assert custody.format_proof(prf) == proof.format_proof(prf)


def test_format_proof_flags_missing_via_core(tmp_path):
    prf = custody.build_proof(0, 0, [_entry(tmp_path / 'gone.bin')])
    text = '\n'.join(custody.format_proof(prf))
    assert 'WARNING' in text
    assert '0/1' in text


def test_disk_free_and_volume_of_via_core(tmp_path):
    assert custody.disk_free(tmp_path) == proof.disk_free(tmp_path)
    assert custody.volume_of(tmp_path) == proof.volume_of(tmp_path)
    assert custody.disk_free(tmp_path) > 0
