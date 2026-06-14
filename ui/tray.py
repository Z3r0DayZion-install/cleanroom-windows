"""Windows notification-area tray for Cleanroom — optional, failure-safe."""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import brand

_active_tray = None


def _resource_path(name):
    here = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    candidate = here / name
    if candidate.exists():
        return candidate
    return Path(getattr(sys, '_MEIPASS', str(Path(__file__).resolve().parent.parent))) / name


def _load_tray_image():
    from PIL import Image

    for rel in (
        'assets/brand/cleanroom-icon.png',
        'cleanroom-icon.png',
    ):
        path = _resource_path(rel)
        if not path.is_file():
            path = brand.ICON_PNG_PATH if rel.endswith('.png') else brand.ICON_ICO_PATH
        if path.is_file():
            img = Image.open(path)
            return img.convert('RGBA') if img.mode != 'RGBA' else img
    return Image.new('RGBA', (64, 64), (59, 130, 246, 255))


def _ensure_icon_running_attr(icon) -> None:
    """pystray Icon.__del__ reads _running; set it before stop/GC to avoid tracebacks."""
    if icon is not None and not hasattr(icon, '_running'):
        icon._running = False


def _patch_pystray_icon_lifecycle() -> None:
    """Ensure Icon always has _running and __del__ never raises."""
    try:
        import pystray
        from pystray import _win32
    except Exception:
        return

    targets = []
    for cls in (getattr(pystray, 'Icon', None), getattr(_win32, 'Icon', None)):
        if cls is not None and cls not in targets:
            targets.append(cls)

    for cls in targets:
        if getattr(cls, '_cleanroom_lifecycle_patched', False):
            continue
        orig_init = cls.__init__
        orig_del = cls.__del__

        def _init(self, *args, _orig=orig_init, **kwargs):
            _orig(self, *args, **kwargs)
            _ensure_icon_running_attr(self)

        def _del(self, _orig=orig_del):
            _ensure_icon_running_attr(self)
            try:
                _orig(self)
            except Exception:
                pass

        cls.__init__ = _init
        cls.__del__ = _del
        cls._cleanroom_lifecycle_patched = True


_patch_pystray_icon_lifecycle()


class TrayController:
    """System tray with product menu hierarchy and live proof-status tooltip."""

    MENU_LABELS = (
        'Open Cleanroom',
        'Run Scan',
        'Preview Latest Receipt',
        'Open Latest Receipt',
        'Open Proof Pack',
        'Open Archive Folder',
        'Explorer Context Menus',
        'Registry Snapshot',
        'Cleanroom Rewind',
        'Custody Check',
        'Hide to tray',
        'Show',
        'Restore',
        'Quit Cleanroom',
    )

    def __init__(self, app):
        self._app = app
        self._icon = None
        self._thread = None
        self._stopping = False

    def start(self):
        global _active_tray
        try:
            import pystray  # noqa: F401
        except ImportError:
            return False
        if _active_tray is not None and _active_tray is not self:
            try:
                _active_tray.stop()
            except Exception:
                pass
            _active_tray = None
        if self._thread and self._thread.is_alive():
            _active_tray = self
            return True
        self._stopping = False
        self._thread = threading.Thread(target=self._run, name='cleanroom-tray', daemon=True)
        self._thread.start()
        _active_tray = self
        return True

    def stop(self):
        global _active_tray
        self._stopping = True
        icon = self._icon
        self._icon = None
        if icon is not None:
            _ensure_icon_running_attr(icon)
            try:
                icon.stop()
            except Exception:
                pass
            finally:
                try:
                    icon._running = False
                except Exception:
                    pass
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.5)
        self._thread = None
        if _active_tray is self:
            _active_tray = None

    def refresh_tooltip(self):
        icon = self._icon
        if icon is None:
            return
        try:
            icon.title = self._tooltip_text()
        except Exception:
            pass

    def _tooltip_text(self) -> str:
        app = self._app
        try:
            if hasattr(app, 'get_tray_tooltip'):
                return app.get_tray_tooltip()
        except Exception:
            pass
        try:
            if hasattr(app, 'global_status'):
                txt = app.global_status.cget('text')
                if txt:
                    return f'{brand.APP_DISPLAY} — {txt}'
        except Exception:
            pass
        return f'{brand.APP_DISPLAY} — Archive-first ON'

    def _status_menu_text(self) -> str:
        tip = self._tooltip_text()
        if ' — ' in tip:
            return tip.split(' — ', 1)[1]
        return 'Archive-first ON'

    def _can_scan(self) -> bool:
        try:
            if hasattr(self._app, 'cleanup_progress') and self._app.cleanup_progress.winfo_ismapped():
                return False
        except Exception:
            pass
        return True

    def _can_preview_receipt(self) -> bool:
        items = getattr(self._app, 'cleanup_items', None) or []
        selected = getattr(self._app, 'cleanup_selected', None) or set()
        return bool(items and selected)

    def _build_menu(self):
        from pystray import Menu, MenuItem as item

        def _status_item(text):
            return item(lambda t: self._status_menu_text(), lambda: None, enabled=False)

        return Menu(
            _status_item('status'),
            Menu.SEPARATOR,
            item('Open Cleanroom', self._on_open),
            item('Run Scan', self._on_run_scan, enabled=lambda _: self._can_scan()),
            item('Preview Latest Receipt', self._on_preview_receipt,
                 enabled=lambda _: self._can_preview_receipt()),
            item('Open Latest Receipt', self._on_latest_receipt),
            item('Open Proof Pack', self._on_proof_pack),
            item('Open Archive Folder', self._on_archive_folder),
            Menu.SEPARATOR,
            Menu(
                'Tools',
                item('Explorer Context Menus', self._on_explorer_menus),
                item('Registry Snapshot', self._on_registry_snapshot),
                item('Cleanroom Rewind', self._on_rewind),
                item('Custody Check', self._on_custody_check),
            ),
            Menu(
                'Window',
                item('Hide to tray', self._on_hide),
                item('Show', self._on_show),
                item('Restore', self._on_restore_tab),
            ),
            Menu.SEPARATOR,
            item('Quit Cleanroom', self._on_quit),
        )

    def _run(self):
        icon = None
        try:
            import pystray

            image = _load_tray_image()
            icon = pystray.Icon(
                'Cleanroom',
                image,
                self._tooltip_text(),
                menu=self._build_menu,
            )
            _ensure_icon_running_attr(icon)
            if self._stopping:
                return
            self._icon = icon
            icon.run()
        except Exception:
            pass
        finally:
            if self._icon is icon:
                self._icon = None
            if icon is not None:
                try:
                    icon._running = False
                except Exception:
                    pass

    def _schedule(self, fn):
        try:
            self._app.after(0, fn)
        except Exception:
            pass

    def _on_open(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_hide(self, icon, item):
        self._schedule(self._app._tray_hide_window)

    def _on_show(self, icon, item):
        self._schedule(self._app._tray_show_window)

    def _on_run_scan(self, icon, item):
        self._schedule(self._app.refresh_cleanup)

    def _on_preview_receipt(self, icon, item):
        self._schedule(self._app.preview_cleanup_receipt)

    def _on_latest_receipt(self, icon, item):
        self._schedule(self._app.open_last_receipt)

    def _on_proof_pack(self, icon, item):
        self._schedule(self._app.export_audit)

    def _on_archive_folder(self, icon, item):
        self._schedule(self._app.open_archive_folder)

    def _on_explorer_menus(self, icon, item):
        self._schedule(self._app.open_shell_context_menu_tool)

    def _on_registry_snapshot(self, icon, item):
        self._schedule(self._app.open_registry_health)

    def _on_rewind(self, icon, item):
        self._schedule(self._app.open_time_machine)

    def _on_custody_check(self, icon, item):
        self._schedule(self._app.verify_custody)

    def _on_restore_tab(self, icon, item):
        def _go():
            try:
                self._app.tab_control.select(self._app.restore_tab)
                self._app.refresh_restore()
                self._app._tray_show_window()
            except Exception:
                self._app._tray_show_window()

        self._schedule(_go)

    def _on_quit(self, icon, item):
        self._schedule(self._app._tray_quit)
