#!/usr/bin/env python3
"""In-app Cleanroom receipt viewer — branded dark modal with summary + raw text."""
from __future__ import annotations

import os
import re
import tkinter as tk

import customtkinter as ctk

from ui import ctk_theme
from ui.product_dialogs import CleanroomModal


def _parse_receipt_meta(text: str) -> dict:
    body = text or ''
    meta = {
        'kind': 'Receipt',
        'timestamp': '',
        'items': '',
        'bytes': '',
        'proof': '',
    }
    upper = body.upper()
    if 'PRUNE RECEIPT' in upper:
        meta['kind'] = 'Prune Archive'
        meta['proof'] = 'Archive-only removal. Original live files were not touched.'
    elif 'PREVIEW ONLY' in upper:
        meta['kind'] = 'Preview Receipt'
        meta['proof'] = 'Preview only — nothing has been archived yet.'
    else:
        meta['proof'] = (
            'Nothing was deleted. Archived items can be restored from Restore or Cleanroom Rewind.'
        )
    m = re.search(r'Date:\s+(\S+\s+\S+)', body)
    if m:
        meta['timestamp'] = m.group(1).strip()
    for pat, key in (
        (r'Items moved:\s+(\d+)', 'items'),
        (r'Items pruned:\s+(\d+)', 'items'),
        (r'Space moved:\s+(\S+)', 'bytes'),
        (r'Bytes pruned:\s+(\S+)', 'bytes'),
    ):
        m = re.search(pat, body, re.I)
        if m:
            meta[key] = m.group(1)
    return meta


class ReceiptViewerDialog:
    """Dark Cleanroom receipt modal."""

    def __init__(
        self,
        parent,
        text,
        title='Receipt',
        receipt_path=None,
        preview=False,
        bg='#1a1d24',
        card='#262c36',
        text_fg='#e5e7eb',
        accent='#3b82f6',
        muted='#9ca3af',
        border='#39414e',
        on_accent='#ffffff',
        **_kwargs,
    ):
        self._receipt_path = receipt_path
        self._text_body = text or ''
        colors = dict(
            bg=bg, card=card, accent=accent, text=text_fg,
            muted=muted, border=border, on_accent=on_accent, head=card,
        )
        meta = _parse_receipt_meta(self._text_body)
        if preview:
            meta['kind'] = 'Preview Receipt'
            meta['proof'] = 'Preview only — nothing has been archived yet.'

        self._modal = CleanroomModal(
            parent, title, width=660, height=580, colors=colors, resizable=True,
        )
        self._modal.heading('Receipt', size=13)
        title_line = meta['kind']
        if meta['timestamp']:
            title_line = f"{meta['kind']} · {meta['timestamp']}"
        ctk_theme.label(
            self._modal.body, title_line, text_color=text_fg,
            font_size=16, weight='bold',
        ).pack(anchor='w', pady=(4, 0))

        stats = ctk.CTkFrame(self._modal.body, fg_color=card)
        stats.pack(fill='x', pady=(10, 0))
        if meta['items']:
            ctk_theme.label(
                stats, f"Items: {meta['items']}", text_color=text_fg, font_size=11,
            ).pack(anchor='w')
        if meta['bytes']:
            ctk_theme.label(
                stats, f"Size: {meta['bytes']}", text_color=text_fg, font_size=11,
            ).pack(anchor='w', pady=(2, 0))
        if meta['proof']:
            ctk_theme.label(
                stats, meta['proof'], text_color=muted,
                font_size=10, wraplength=580, justify='left',
            ).pack(anchor='w', pady=(8, 0))

        tabs = ctk.CTkTabview(
            self._modal.body, fg_color=card, segmented_button_fg_color=bg,
            segmented_button_selected_color=accent,
            segmented_button_unselected_color=card,
            text_color=text_fg,
        )
        tabs.pack(fill='both', expand=True, pady=(12, 0))
        summary_tab = tabs.add('Summary')
        raw_tab = tabs.add('Raw receipt')

        summary = tk.Text(
            summary_tab, wrap='word', font=('Segoe UI', 10),
            bg=card, fg=text_fg, relief='flat', padx=8, pady=8,
        )
        summary.pack(fill='both', expand=True)
        summary.insert('1.0', self._summarize_body(meta))
        summary.configure(state='disabled')

        raw_wrap = ctk.CTkFrame(raw_tab, fg_color=card)
        raw_wrap.pack(fill='both', expand=True)
        raw = tk.Text(
            raw_wrap, wrap='word', font=('Consolas', 10),
            bg='#0f1419', fg=text_fg, relief='flat', padx=10, pady=10,
        )
        scroll = ctk.CTkScrollbar(raw_wrap, command=raw.yview)
        raw.configure(yscrollcommand=scroll.set)
        raw.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        raw.insert('1.0', self._text_body)
        raw.configure(state='disabled')

        self._modal.add_button('Copy Receipt', self._copy, side='left')
        if receipt_path:
            self._modal.add_button('Open Receipt File', self._open_file, side='left')
            self._modal.add_button('Open Receipt Folder', self._open_folder, side='left')
        self._modal.add_button('Close', self._modal.close, primary=True)

    def _summarize_body(self, meta: dict) -> str:
        lines = [f"Type: {meta['kind']}"]
        if meta['timestamp']:
            lines.append(f"When: {meta['timestamp']}")
        if meta['items']:
            lines.append(f"Items: {meta['items']}")
        if meta['bytes']:
            lines.append(f"Total size: {meta['bytes']}")
        lines.extend(['', meta.get('proof') or '', '', 'See Raw receipt tab for full proof text.'])
        return '\n'.join(lines)

    def _copy(self):
        try:
            root = self._modal.win
            root.clipboard_clear()
            root.clipboard_append(self._text_body)
            root.update_idletasks()
        except tk.TclError:
            pass

    def _open_file(self):
        path = self._receipt_path
        if not path or not os.path.isfile(str(path)):
            return
        try:
            os.startfile(str(path))
        except OSError:
            pass

    def _open_folder(self):
        if not self._receipt_path:
            return
        folder = os.path.dirname(str(self._receipt_path))
        if os.path.isdir(folder):
            try:
                os.startfile(folder)
            except OSError:
                pass


def show_receipt(parent, text, receipt_path=None, preview=False, **kwargs):
    return ReceiptViewerDialog(parent, text, receipt_path=receipt_path, preview=preview, **kwargs)
