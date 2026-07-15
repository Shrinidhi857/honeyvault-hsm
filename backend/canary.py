"""
canary.py
Logs canary beacon hits — triggered when attacker opens a fake vault entry.
"""

import json, datetime, os

CANARY_LOG = 'canary_log.json'

def log_hit(ref: str, ip: str, user_agent: str, password_used: str = ''):
    """Append a canary hit to the log file."""
    entry = {
        'timestamp':     datetime.datetime.now().isoformat(),
        'ref':           ref,
        'ip':            ip,
        'user_agent':    user_agent,
        'password_used': password_used
    }
    hits = get_hits()
    hits.append(entry)
    with open(CANARY_LOG, 'w') as f:
        json.dump(hits, f, indent=2)

def get_hits() -> list:
    """Return all canary hits."""
    if not os.path.exists(CANARY_LOG):
        return []
    with open(CANARY_LOG, 'r') as f:
        return json.load(f)