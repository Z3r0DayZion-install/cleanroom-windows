#!/usr/bin/env python3
"""Generate SHA256SUMS.txt from built release artifacts in dist/."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', required=True, help='Release version, e.g. 1.0.0')
    args = parser.parse_args()

    dist = ROOT / 'dist'
    artifacts: list[tuple[Path, str]] = []

    installer = dist / f'Cleanroom-Setup-{args.version}.exe'
    if installer.is_file():
        artifacts.append((installer, installer.name))

    portable = dist / 'Cleanroom' / 'Cleanroom.exe'
    if portable.is_file():
        artifacts.append((portable, 'Cleanroom/Cleanroom.exe'))

    if not artifacts:
        print('No release artifacts found in dist/', file=sys.stderr)
        return 1

    lines = [f'# Cleanroom v{args.version} release checksums (SHA256)']
    for path, name in artifacts:
        lines.append(f'{_sha256(path)}  {name}')

    out = ROOT / 'SHA256SUMS.txt'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Wrote {out} ({len(artifacts)} artifact(s))')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
