#!/usr/bin/env python3
"""Safe registry health scanning (archive-first).

Unlike "registry cleaner" snake oil, this only flags entries that verifiably
point at files that no longer exist:

- dead startup refs:   Run-key values whose command's executable is missing
- broken App Paths:    App Paths keys whose target executable is missing
- orphaned uninstalls: Programs-list entries whose uninstaller exe is missing

Every fix is reversible: values/keys are exported to .reg files in the archive
before deletion and logged to the cleanup log (reason 'broken-registry'), so
the Restore tab and Time Machine can re-import them.
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import uninstaller

REG_PREFIX = uninstaller.REG_PREFIX

RUN_KEYS = [
    ('HKEY_CURRENT_USER', r'Software\Microsoft\Windows\CurrentVersion\Run'),
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run'),
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run'),
]

APP_PATH_KEYS = [
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'),
    ('HKEY_LOCAL_MACHINE', r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths'),
    ('HKEY_CURRENT_USER', r'Software\Microsoft\Windows\CurrentVersion\App Paths'),
]

# Host launchers take their real target as an *argument*; judging whether that
# target is broken is unreliable, so commands run through these are never flagged.
_HOST_LAUNCHERS = {'rundll32', 'rundll32.exe', 'regsvr32', 'regsvr32.exe',
                   'cmd', 'cmd.exe', 'powershell', 'powershell.exe', 'pwsh',
                   'pwsh.exe', 'wscript', 'wscript.exe', 'cscript', 'cscript.exe',
                   'mshta', 'mshta.exe', 'explorer', 'explorer.exe',
                   'msiexec', 'msiexec.exe'}


def extract_exe_path(command, exists=os.path.exists):
    """Best-effort executable path from a registry command line.

    Quoted commands take the quoted segment. Unquoted commands try the longest
    space-joined prefix that exists on disk, falling back to the first token.
    Returns None for empty commands.
    """
    cmd = os.path.expandvars(str(command or '').strip())
    if not cmd:
        return None
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        return cmd[1:end] if end > 1 else None
    parts = cmd.split(' ')
    for i in range(len(parts), 0, -1):
        cand = ' '.join(parts[:i])
        if exists(cand):
            return cand
    return parts[0]


def is_broken_command(command, exists=os.path.exists, which=shutil.which):
    """True when the command's executable verifiably does not exist.

    Conservative: host launchers (rundll32, cmd, ...), PATH-resolvable names
    and anything ambiguous count as healthy.
    """
    exe = extract_exe_path(command, exists=exists)
    if not exe:
        return False
    base = os.path.basename(exe).lower()
    if base in _HOST_LAUNCHERS:
        return False
    if exists(exe) or exists(exe + '.exe'):
        return False
    if '\\' not in exe and '/' not in exe:
        # bare name: resolved via PATH / App Paths at run time
        return not which(exe) and not which(exe + '.exe')
    return True


# ---------------------------------------------------------------------------
# scanners (registry enumeration is injectable for tests)
# ---------------------------------------------------------------------------
def _enum_values(hive_name, key_path):
    """Yield (value_name, value) string values of a key; [] off-Windows."""
    try:
        import winreg
    except Exception:
        return
    hive = getattr(winreg, hive_name, None)
    if hive is None:
        return
    try:
        with winreg.OpenKey(hive, key_path) as k:
            i = 0
            while True:
                try:
                    name, value, vtype = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if vtype in (winreg.REG_SZ, winreg.REG_EXPAND_SZ) and name:
                    yield name, str(value)
    except Exception:
        return


def _enum_app_paths(hive_name, key_path):
    """Yield (subkey_name, default_value) for each App Paths subkey."""
    try:
        import winreg
    except Exception:
        return
    hive = getattr(winreg, hive_name, None)
    if hive is None:
        return
    try:
        with winreg.OpenKey(hive, key_path) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as k:
                        default, _ = winreg.QueryValueEx(k, '')
                except Exception:
                    continue
                if default:
                    yield sub, str(default)
    except Exception:
        return


def scan_dead_startup_refs(values=None, exists=os.path.exists, which=shutil.which):
    """Run-key values whose command points at a missing executable.

    `values`: optional [(hive_name, key_path, value_name, command), ...] for
    tests; defaults to enumerating the real Run keys."""
    if values is None:
        values = [(h, k, name, cmd)
                  for h, k in RUN_KEYS
                  for name, cmd in _enum_values(h, k)]
    issues = []
    for hive_name, key_path, name, cmd in values:
        if is_broken_command(cmd, exists=exists, which=which):
            issues.append({
                'type': 'startup-ref', 'fix': 'delete-value',
                'hive': hive_name, 'key': key_path, 'value_name': name,
                'display': name,
                'detail': f'startup command points to missing file: {cmd}',
            })
    return issues


def scan_broken_app_paths(entries=None, exists=os.path.exists):
    """App Paths registrations whose target executable is missing.

    `entries`: optional [(hive_name, key_path, subkey, target), ...] for tests."""
    if entries is None:
        entries = [(h, k, sub, target)
                   for h, k in APP_PATH_KEYS
                   for sub, target in _enum_app_paths(h, k)]
    issues = []
    for hive_name, key_path, sub, target in entries:
        t = os.path.expandvars(target.strip().strip('"'))
        if t and not exists(t):
            issues.append({
                'type': 'app-path', 'fix': 'delete-key',
                'hive': hive_name, 'key': f'{key_path}\\{sub}', 'value_name': None,
                'display': sub,
                'detail': f'App Paths target missing: {t}',
            })
    return issues


def scan_orphaned_uninstall_entries(programs=None, exists=os.path.exists,
                                    which=shutil.which):
    """Programs-list entries whose uninstaller executable is gone."""
    if programs is None:
        programs = uninstaller.list_installed_programs()
    issues = []
    for entry in programs:
        cmd = entry.get('uninstall_string') or ''
        if not cmd or cmd.lower().lstrip('"').startswith('msiexec'):
            continue  # MSI entries are serviced by Windows Installer itself
        if is_broken_command(cmd, exists=exists, which=which):
            issues.append({
                'type': 'uninstall-entry', 'fix': 'delete-key',
                'hive': entry.get('hive', ''),
                'key': f"{entry.get('key', '')}\\{entry.get('subkey', '')}",
                'value_name': None,
                'display': entry.get('name', entry.get('subkey', '')),
                'detail': f'uninstaller missing: {cmd}',
            })
    return issues


def find_registry_issues():
    """All verifiable registry issues, grouped by scanner."""
    return (scan_dead_startup_refs()
            + scan_broken_app_paths()
            + scan_orphaned_uninstall_entries())


# ---------------------------------------------------------------------------
# repair (archive-first)
# ---------------------------------------------------------------------------
def _escape_reg_string(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def format_value_reg(hive_name, key_path, value_name, value, expand=False):
    """A .reg file that recreates a single string value (restore = import)."""
    if expand:
        # REG_EXPAND_SZ is stored as hex(2): UTF-16LE bytes incl. terminator
        data = (str(value) + '\x00').encode('utf-16-le')
        hexed = ','.join(f'{b:02x}' for b in data)
        line = f'"{_escape_reg_string(value_name)}"=hex(2):{hexed}'
    else:
        line = f'"{_escape_reg_string(value_name)}"="{_escape_reg_string(str(value))}"'
    return ('Windows Registry Editor Version 5.00\r\n\r\n'
            f'[{hive_name}\\{key_path}]\r\n{line}\r\n')


def export_value(hive_name, key_path, value_name, out_file):
    """Export one value to a .reg file. Returns True on success."""
    try:
        import winreg
        hive = getattr(winreg, hive_name)
        with winreg.OpenKey(hive, key_path) as k:
            value, vtype = winreg.QueryValueEx(k, value_name)
        text = format_value_reg(hive_name, key_path, value_name, value,
                                expand=(vtype == winreg.REG_EXPAND_SZ))
        Path(out_file).write_text(text, encoding='utf-16')
        return True
    except Exception:
        return False


def delete_value(hive_name, key_path, value_name):
    try:
        import winreg
        hive = getattr(winreg, hive_name)
        with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, value_name)
        return True
    except Exception:
        return False


def archive_registry_issues(issues, archive_dir, log_file,
                            export_key_fn=uninstaller.export_registry_key,
                            delete_key_fn=uninstaller.delete_registry_key,
                            export_value_fn=export_value,
                            delete_value_fn=delete_value):
    """Fix issues archive-first: export the value/key to .reg, then delete it.
    Logs restorable entries (reason 'broken-registry'). Returns the log list."""
    dest_root = Path(archive_dir) / 'registry_health'
    dest_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d%H%M%S')
    log_entries = []
    for n, issue in enumerate(issues):
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', issue['display'])[:80]
        out = dest_root / f'{stamp}_{n}_{safe}.reg'
        if issue['fix'] == 'delete-value':
            ok = (export_value_fn(issue['hive'], issue['key'], issue['value_name'], out)
                  and delete_value_fn(issue['hive'], issue['key'], issue['value_name']))
            src = f"{REG_PREFIX}{issue['hive']}\\{issue['key']} :: {issue['value_name']}"
        else:
            full_key = f"{issue['hive']}\\{issue['key']}"
            ok = export_key_fn(full_key, out) and delete_key_fn(full_key)
            src = REG_PREFIX + full_key
        if not ok:
            try:
                out.unlink()
            except Exception:
                pass
            continue
        try:
            size = out.stat().st_size
        except Exception:
            size = 0
        log_entries.append({
            'src': src,
            'dest': str(out),
            'reason': 'broken-registry',
            'size': size,
            'when': datetime.now().isoformat(),
        })
    if log_entries:
        uninstaller._append_log(log_file, log_entries)
    return log_entries
