"""Theme palette integrity tests (no display required)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import startup_manager_gui as gui

HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
REASON_KEYS = {'large-file', 'installer/archive', 'partial-download',
               'zero-byte', 'uninstall-leftover', 'registry-leftover', 'broken-registry'}
SEVERITY_KEYS = {'high', 'medium', 'low', 'info'}


def test_theme_order_matches_palettes():
    assert set(gui.THEME_ORDER) == set(gui.PALETTES.keys())


def test_every_palette_defines_all_keys_with_valid_colors():
    for name, p in gui.PALETTES.items():
        assert p.get('LABEL'), f'{name} missing LABEL'
        for key in gui.THEME_KEYS:
            assert key in p, f'{name} missing {key}'
            assert HEX.match(p[key]), f'{name}.{key} = {p[key]!r} not a hex color'
        assert set(p['SEVERITY'].keys()) == SEVERITY_KEYS, f'{name} severity keys'
        assert set(p['REASONS'].keys()) == REASON_KEYS, f'{name} reason keys'
        for v in list(p['SEVERITY'].values()) + list(p['REASONS'].values()):
            assert HEX.match(v)


def test_apply_palette_sets_module_globals():
    original = gui.CURRENT_THEME
    try:
        for name in gui.THEME_ORDER:
            gui.apply_palette(name)
            assert gui.CURRENT_THEME == name
            assert gui.BG == gui.PALETTES[name]['BG']
            assert gui.ON_ACCENT == gui.PALETTES[name]['ON_ACCENT']
            assert gui.REASON_COLORS == gui.PALETTES[name]['REASONS']
    finally:
        gui.apply_palette(original)


def test_apply_palette_unknown_falls_back_to_dark():
    original = gui.CURRENT_THEME
    try:
        gui.apply_palette('does-not-exist')
        assert gui.CURRENT_THEME == 'dark'
        assert gui.BG == gui.PALETTES['dark']['BG']
    finally:
        gui.apply_palette(original)
