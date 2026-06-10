"""Tests for brand.py — migration and data dir resolution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import brand


def test_user_data_dir_always_cleanroom(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert brand.user_data_dir() == tmp_path / 'Cleanroom'
    assert (tmp_path / 'Cleanroom').is_dir()


def test_migration_copies_legacy_and_leaves_backup(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    brand._migrated = False
    legacy = tmp_path / 'SmartClean'
    legacy.mkdir()
    (legacy / 'receipts').mkdir()
    (legacy / 'receipts' / 'old.txt').write_text('legacy data', encoding='utf-8')
    (legacy / 'ui_prefs.json').write_text('{}', encoding='utf-8')

    migrated, receipt = brand.migrate_legacy_data()
    assert migrated is True
    assert receipt is not None
    assert receipt.exists()
    assert 'MIGRATION RECEIPT' in receipt.read_text(encoding='utf-8')
    assert (tmp_path / 'Cleanroom' / 'receipts' / 'old.txt').read_text() == 'legacy data'
    assert (legacy / 'receipts' / 'old.txt').exists()  # backup untouched

    # Second run is idempotent
    again, path = brand.migrate_legacy_data()
    assert again is False


def test_user_data_dir_migrates_on_first_access(tmp_path, monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    brand._migrated = False
    legacy = tmp_path / 'SmartClean'
    legacy.mkdir()
    (legacy / 'disk_history.json').write_text('[]', encoding='utf-8')

    dest = brand.user_data_dir()
    assert dest == tmp_path / 'Cleanroom'
    assert (dest / 'migration_receipt.txt').exists()
    assert (dest / 'disk_history.json').exists()
    assert (legacy / 'disk_history.json').exists()


def test_cleanroom_wins_when_both_exist_without_receipt(tmp_path, monkeypatch):
    """If both dirs exist but no migration ran, migrate merges missing files."""
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    brand._migrated = False
    legacy = tmp_path / 'SmartClean'
    clean = tmp_path / 'Cleanroom'
    legacy.mkdir()
    clean.mkdir()
    (legacy / 'only_in_legacy.txt').write_text('x', encoding='utf-8')

    brand.migrate_legacy_data()
    assert (clean / 'only_in_legacy.txt').read_text() == 'x'
    assert (clean / 'migration_receipt.txt').exists()
