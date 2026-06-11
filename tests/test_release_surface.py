"""Tests for scripts/verify_release_surface.py gates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

import verify_release_surface as vrs  # noqa: E402


def test_public_docs_have_release_urls():
    assert vrs.scan_public_docs() is True


def test_screenshot_assets_present():
    assert vrs.scan_screenshot_assets() is True


def test_forbidden_ui_labels_clean():
    assert vrs.scan_forbidden_ui_labels() is True
