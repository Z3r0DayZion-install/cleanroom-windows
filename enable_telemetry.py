# telemetry helpers (placeholder)
import json
from datetime import datetime
from pathlib import Path

TEL_PATH = Path(__file__).parent / 'telemetry.json'

def is_opted_in():
    try:
        if not TEL_PATH.exists():
            return False
        with open(TEL_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return bool(data.get('opt_in'))
    except Exception:
        return False

def set_opt_in(v: bool):
    try:
        payload = {'opt_in': bool(v), 'ts': datetime.now().isoformat()}
        with open(TEL_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        return True
    except Exception:
        return False
#!/usr/bin/env python3
import sys
import json
from pathlib import Path

CFG = Path(__file__).parent / 'cleanup_config.yaml'
try:
    import yaml
except Exception:
    yaml = None


def load_yaml(p):
    text = p.read_text(encoding='utf-8')
    if yaml:
        return yaml.safe_load(text)
    import ruamel.yaml as ry
    return ry.YAML().load(text)


def write_yaml(p, obj):
    if yaml:
        p.write_text(yaml.safe_dump(obj), encoding='utf-8')
    else:
        import ruamel.yaml as ry
        ry.YAML().dump(obj, p.open('w', encoding='utf-8'))


def main(enable=True):
    if not CFG.exists():
        print('Config not found:', CFG)
        return 2
    # simple parsing: treat as YAML-like by using ruamel if PyYAML not available
    try:
        cfg = load_yaml(CFG)
    except Exception as e:
        print('Failed to parse config:', e)
        return 2
    tele = cfg.get('telemetry') or {}
    tele['enabled'] = bool(enable)
    cfg['telemetry'] = tele
    try:
        write_yaml(CFG, cfg)
    except Exception as e:
        print('Failed to write config:', e)
        return 2
    print(f"Telemetry {'enabled' if enable else 'disabled'} in {CFG}")
    return 0

if __name__ == '__main__':
    ok = True
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('off','false','0','disable'):
            ok = False
    rc = main(enable=ok)
    sys.exit(rc)
