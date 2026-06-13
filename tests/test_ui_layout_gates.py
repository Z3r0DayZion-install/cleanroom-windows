"""Window geometry defaults for responsive layout."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ui import window_geometry


def test_default_and_minimum_window_sizes():
    assert window_geometry.DEFAULT_SIZE == (1320, 800)
    assert window_geometry.MIN_SIZE[0] >= 1080
    assert window_geometry.MIN_SIZE[1] >= 660
