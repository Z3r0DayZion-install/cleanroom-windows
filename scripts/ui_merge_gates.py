#!/usr/bin/env python3
"""Pre-merge UI gates: scaling/layout checks for CustomTkinter shell.

Run on ui/local-only-polish before merging PR #6:
  python scripts/ui_merge_gates.py
  python scripts/ui_merge_gates.py --packaged dist/Cleanroom/Cleanroom.exe
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GEOMETRIES = (
    (1240, 760, '1240x760'),
    (1366, 768, '1366x768'),
    (1920, 1080, '1920x1080'),
)

TOOLBAR_LABELS = (
    ('tb_scan', 'Scan'),
    ('tb_preview', 'Preview Receipt'),
    ('tb_apply', 'Archive & Clean'),
    ('tb_restore', 'Restore'),
)


def _fail(msg: str) -> None:
    print(f'FAIL: {msg}', file=sys.stderr)


def _ok(msg: str) -> None:
    print(f'OK: {msg}')


def _widget_ok(widget, name: str, min_w: int = 24, min_h: int = 14) -> list[str]:
    issues = []
    try:
        widget.update_idletasks()
        w, h = widget.winfo_width(), widget.winfo_height()
        if w < min_w or h < min_h:
            issues.append(f'{name} too small ({w}x{h})')
        if not widget.winfo_viewable():
            issues.append(f'{name} not viewable')
    except Exception as exc:
        issues.append(f'{name} check error: {exc}')
    return issues


def _find_text_in_tree(widget, needle: str) -> bool:
    try:
        if hasattr(widget, 'cget'):
            text = str(widget.cget('text'))
            if needle in text:
                return True
    except Exception:
        pass
    for child in widget.winfo_children():
        if _find_text_in_tree(child, needle):
            return True
    return False


def check_layout(app, width: int, height: int, label: str) -> list[str]:
    """Return list of layout failures at the given window size."""
    sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    app.geometry(f'{width}x{height}+{x}+{y}')
    app.update_idletasks()
    app.update()
    time.sleep(0.15)

    issues: list[str] = []
    for attr, name in TOOLBAR_LABELS:
        issues.extend(_widget_ok(getattr(app, attr), f'{label}/{name}'))

    issues.extend(_widget_ok(app.hdr_trust_value, f'{label}/Custody Trust value', 20, 16))
    issues.extend(_widget_ok(app.hdr_trust_lbl, f'{label}/Custody Trust label', 40, 12))

    if not _find_text_in_tree(app, 'Preview Receipt'):
        issues.append(f'{label}/proof-flow or Preview Receipt text missing')
    if not _find_text_in_tree(app, 'Archive-first mode is ON'):
        issues.append(f'{label}/archive-first banner missing')

    return issues


def run_scaling_gates() -> int:
    from tkinter import messagebox
    import startup_manager_gui as gui_module

    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)

    app = gui_module.StartupManagerGUI()
    all_issues: list[str] = []
    try:
        for w, h, label in GEOMETRIES:
            issues = check_layout(app, w, h, label)
            if issues:
                all_issues.extend(issues)
                for i in issues:
                    _fail(i)
            else:
                _ok(f'Layout gate passed at {label}')
    finally:
        app.destroy()

    if all_issues:
        print(f'\nScaling gate FAILED ({len(all_issues)} issue(s))', file=sys.stderr)
        return 1
    print('\nScaling gate PASSED (1240x760, 1366x768, 1920x1080)')
    print('NOTE: 150% Windows display scaling must be verified manually.')
    return 0


def run_packaged_smoke(exe: Path, seconds: float = 8.0) -> int:
    if not exe.is_file():
        _fail(f'Packaged EXE not found: {exe}')
        return 1

    profile = Path(tempfile.mkdtemp(prefix='cleanroom-gate-'))
    local = profile / 'LocalAppData'
    local.mkdir()
    cleanroom = local / 'Cleanroom'
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(local)

    _ok(f'Fresh profile LOCALAPPDATA={local}')
    proc = subprocess.Popen(
        [str(exe)],
        cwd=str(exe.parent),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(seconds)
    code = proc.poll()
    if code is not None:
        _fail(f'Packaged EXE exited early with code {code}')
        return 1
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    if cleanroom.exists():
        _ok(f'Cleanroom data dir created: {cleanroom}')
    else:
        _ok('No data dir yet (OK if first launch made no writes)')

    internal = exe.parent / '_internal' / 'customtkinter'
    if internal.is_dir():
        _ok('customtkinter assets present in _internal')
    else:
        _fail('customtkinter _internal folder missing')
        return 1

    print('\nPackaged smoke PASSED (fresh LOCALAPPDATA, CTk assets present)')
    print('NOTE: Full clean-machine installer test still required manually.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packaged', metavar='EXE', default='',
                        help='Also run packaged EXE smoke test')
    parser.add_argument('--scaling-only', action='store_true')
    args = parser.parse_args()

    rc = 0
    if not args.scaling_only:
        pass
    rc = run_scaling_gates()
    if args.packaged:
        rc = max(rc, run_packaged_smoke(Path(args.packaged)))
    elif Path('dist/Cleanroom/Cleanroom.exe').is_file():
        rc = max(rc, run_packaged_smoke(Path('dist/Cleanroom/Cleanroom.exe')))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
