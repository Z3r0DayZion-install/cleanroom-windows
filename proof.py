#!/usr/bin/env python3
"""Proof of work: measured evidence that Cleanroom actually did something.

Most optimizers print a made-up number and call it a day. This module
produces evidence that can be independently checked:

- disk free space is measured from the OS (shutil.disk_usage) before and
  after an operation — never estimated from summed file sizes
- a "custody check" verifies that every archived artifact (moved file or
  exported .reg) actually exists on disk right now, so the reversibility
  promise is checkable at any time, not just claimed

Implementation lives in receipt_core.custody; this module re-exports for
backward compatibility.
"""
from receipt_core.custody import (
    build_proof,
    disk_free,
    format_proof,
    verify_entries,
    volume_of,
)

REG_PREFIX = 'REGISTRY::'

__all__ = (
    'REG_PREFIX',
    'build_proof',
    'disk_free',
    'format_proof',
    'verify_entries',
    'volume_of',
)
