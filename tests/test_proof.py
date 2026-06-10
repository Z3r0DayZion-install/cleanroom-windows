"""Unit tests for proof.py — OS-measured evidence + custody checks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import proof
import receipts


def _entry(dest, size=10, src=None, reason='large-file'):
    return {'src': src or f'C:\\junk\\{Path(dest).name}', 'dest': str(dest),
            'reason': reason, 'size': size, 'when': '2026-06-10T12:00:00'}


def test_verify_entries_counts_present_and_missing(tmp_path):
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
    result = proof.verify_entries(entries)
    assert result['total'] == 3
    assert result['verified'] == 2
    assert result['missing'] == 1
    assert result['bytes_in_custody'] == 64 + 32
    assert any('gone.bin' in m for m in result['missing_items'])


def test_verify_entries_skips_destless_records():
    result = proof.verify_entries([{'src': 'x', 'reason': 'restore'}])
    assert result['total'] == 0
    assert result['missing'] == 0


def test_build_proof_math(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 100)
    prf = proof.build_proof(1000, 1300, [_entry(f, size=100)])
    assert prf['measured_delta'] == 300
    assert prf['claimed_bytes'] == 100
    assert prf['custody']['verified'] == 1


def test_format_proof_explains_moves_not_deletes(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 100)
    # Moved 1 MB but free space barely changed -> must explain archive-first
    prf = proof.build_proof(10_000_000, 10_000_100, [_entry(f, size=1024 * 1024)])
    text = '\n'.join(proof.format_proof(prf))
    assert 'measured by the OS' in text
    assert 'MOVED to the archive' in text
    assert 'Custody check' in text
    assert '1/1' in text


def test_format_proof_flags_missing(tmp_path):
    prf = proof.build_proof(0, 0, [_entry(tmp_path / 'gone.bin')])
    text = '\n'.join(proof.format_proof(prf))
    assert 'WARNING' in text
    assert '0/1' in text


def test_receipt_embeds_proof_section(tmp_path):
    f = tmp_path / 'kept.bin'
    f.write_bytes(b'z' * 50)
    entries = [_entry(f, size=50)]
    prf = proof.build_proof(500, 500, entries)
    text = receipts.format_receipt(entries, proof=prf)
    assert 'PROOF (measured by the OS, not estimated):' in text
    assert 'Custody check' in text
    # and still has the regular receipt body
    assert 'CLEANROOM — RECEIPT' in text
    assert 'Nothing was deleted' in text


def test_receipt_without_proof_unchanged(tmp_path):
    text = receipts.format_receipt([_entry(tmp_path / 'x', size=5)])
    assert 'PROOF' not in text
    assert 'CLEANROOM — RECEIPT' in text


def test_disk_free_and_volume_of(tmp_path):
    assert proof.disk_free(tmp_path) > 0
    vol = proof.volume_of(tmp_path)
    assert vol.endswith('\\') or vol.endswith('/')
    assert proof.disk_free('Z:\\nonexistent\\hopefully') >= 0
