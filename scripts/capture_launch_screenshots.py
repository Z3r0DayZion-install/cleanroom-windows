#!/usr/bin/env python3
"""Capture launch screenshots for README (Review tab, Activity tab, Proof Pack demo)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'screenshots'
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402
import tkinter as tk  # noqa: E402


def _grab_window(app, path: Path):
    app.update_idletasks()
    app.update()
    time.sleep(0.4)
    x, y = app.winfo_rootx(), app.winfo_rooty()
    w, h = app.winfo_width(), app.winfo_height()
    if w < 200 or h < 200:
        w, h = 1240, 700
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f'Wrote {path} ({img.size[0]}x{img.size[1]})')


def _seed_demo_log(tmp: Path, archive: Path):
    """Activity ledger with verified custody (all dest files exist)."""
    entries = []
    samples = [
        ('large-file', 'reviewed_installer.msi', 512 * 1024 * 1024),
        ('temp', 'cache_bundle.zip', 128 * 1024 * 1024),
        ('partial-download', 'video.crdownload', 256 * 1024 * 1024),
    ]
    for reason, name, size in samples:
        src = tmp / 'scan' / name
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(b'x' * min(size, 4096))
        dest = archive / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'x' * min(size, 4096))
        entries.append({
            'src': str(src),
            'dest': str(dest),
            'reason': reason,
            'size': size,
            'when': '2026-06-10T14:00:00',
        })
    log = tmp / 'cleanup_log.json'
    log.write_text(json.dumps(entries, indent=2), encoding='utf-8')
    return log


def capture_gui_screenshots():
    import receipts as receipts_module
    import foresight as foresight_module
    import startup_manager_gui as gui_module
    from tkinter import messagebox

    for fn in ('showinfo', 'showwarning', 'showerror', 'askyesno'):
        setattr(messagebox, fn, lambda *a, **k: True if fn == 'askyesno' else None)
    gui_module.StartupManagerGUI._show_proof_report = lambda *a, **k: None

    tmp = ROOT / '.screenshot_sandbox'
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    scan = tmp / 'scan'
    scan.mkdir()
    archive = tmp / 'archive'
    archive.mkdir()
    # Scan candidates for Review tab
    old = scan / 'reviewed_candidate.zip'
    old.write_text('demo payload', encoding='utf-8')
    old_ts = time.time() - 45 * 86400
    os.utime(old, (old_ts, old_ts))
    log_path = _seed_demo_log(tmp, archive)

    cfg = tmp / 'config.yaml'
    cfg.write_text(
        f'paths:\n  - {scan}\n'
        'age_days:\n  temp: 7\n  installers: 30\n'
        'size_threshold_mb: 200\n'
        "extensions_archive: ['.zip']\n"
        'exclude_patterns: []\nwhitelist: []\n'
        f'archive_dir: {archive}\n'
        f'log_file: {log_path}\n'
        'confirm_threshold_bytes: 99999999999999\n',
        encoding='utf-8')

    receipts_module.RECEIPT_DIR = tmp / 'receipts'
    foresight_module.HISTORY_PATH = tmp / 'disk_history.json'
    foresight_module.HEALTH_PATH = tmp / 'health_history.json'

    app = gui_module.StartupManagerGUI(config_path=cfg, restore_log_path=log_path)
    app.geometry('1240x760')
    app.update()

    # Review tab
    app.tab_control.select(0)
    app.refresh_cleanup()
    pump = lambda: app.cleanup_items or True
    deadline = time.time() + 20
    while time.time() < deadline:
        app.update()
        if app.cleanup_items:
            break
        time.sleep(0.05)
    app.refresh_optimizer()
    app.update()
    time.sleep(0.3)
    _grab_window(app, OUT / 'cleanroom-review.png')

    # Activity tab — verified custody
    app.tab_control.select(1)
    app.refresh_activity()
    app.update()
    time.sleep(0.3)
    _grab_window(app, OUT / 'cleanroom-activity-ledger.png')

    app.destroy()


def capture_proof_pack_html():
    html = (ROOT / 'docs' / 'demo' / 'cleanroom-proof-pack-demo.html').resolve()
    out = OUT / 'cleanroom-proof-pack-demo.png'
    candidates = [
        Path(os.environ.get('PROGRAMFILES', '')) / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', '')) / 'Microsoft/Edge/Application/msedge.exe',
        Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/Application/chrome.exe',
    ]
    browser = next((p for p in candidates if p.is_file()), None)
    if browser is None:
        raise SystemExit('No Edge/Chrome found for headless HTML screenshot')
    url = html.as_uri()
    cmd = [
        str(browser),
        '--headless=new',
        '--disable-gpu',
        '--hide-scrollbars',
        f'--window-size=1280,920',
        f'--screenshot={out}',
        url,
    ]
    subprocess.run(cmd, check=True, timeout=60)
    print(f'Wrote {out}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    capture_gui_screenshots()
    capture_proof_pack_html()
    for name in ('cleanroom-review.png', 'cleanroom-activity-ledger.png', 'cleanroom-proof-pack-demo.png'):
        p = OUT / name
        if not p.is_file():
            raise SystemExit(f'Missing screenshot: {p}')
    print('All launch screenshots captured.')


if __name__ == '__main__':
    main()
