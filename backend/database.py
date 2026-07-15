"""
database.py
SQLite database for HoneyVault.
Stores canary hits, audit logs, and vault metadata.
"""

import sqlite3, datetime, os

DB_FILE = 'honeyvault.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # returns dict-like rows
    return conn

def init_db():
    conn = get_db()
    c    = conn.cursor()

    # Canary / attack log
    c.execute('''
        CREATE TABLE IF NOT EXISTS canary_hits (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT,
            ip            TEXT,
            user_agent    TEXT,
            password_used TEXT,
            ref           TEXT
        )
    ''')

    # Audit log — every vault action
    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            action    TEXT,
            detail    TEXT,
            ip        TEXT
        )
    ''')

    # Vault metadata
    c.execute('''
        CREATE TABLE IF NOT EXISTS vault_meta (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at   TEXT,
            last_unlocked TEXT,
            unlock_count  INTEGER DEFAULT 0,
            failed_count  INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

# ── Canary hits ───────────────────────────────────────────────────────────────

def log_canary_hit(ip, user_agent, password_used, ref):
    conn = get_db()
    conn.execute(
        "INSERT INTO canary_hits (timestamp, ip, user_agent, password_used, ref) VALUES (?,?,?,?,?)",
        (datetime.datetime.now().isoformat(), ip, user_agent, password_used, ref)
    )
    conn.commit()
    conn.close()

def get_canary_hits():
    conn  = get_db()
    rows  = conn.execute("SELECT * FROM canary_hits ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Audit log ─────────────────────────────────────────────────────────────────

def log_action(action, detail, ip):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_log (timestamp, action, detail, ip) VALUES (?,?,?,?)",
        (datetime.datetime.now().isoformat(), action, detail, ip)
    )
    conn.commit()
    conn.close()

def get_audit_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Vault metadata ────────────────────────────────────────────────────────────

def create_vault_meta():
    conn = get_db()
    # Only one row ever exists
    existing = conn.execute("SELECT * FROM vault_meta").fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO vault_meta (created_at, last_unlocked, unlock_count, failed_count) VALUES (?,?,?,?)",
            (datetime.datetime.now().isoformat(), None, 0, 0)
        )
        conn.commit()
    conn.close()

def update_vault_meta(success: bool):
    conn = get_db()
    if success:
        conn.execute(
            "UPDATE vault_meta SET last_unlocked=?, unlock_count=unlock_count+1",
            (datetime.datetime.now().isoformat(),)
        )
    else:
        conn.execute("UPDATE vault_meta SET failed_count=failed_count+1")
    conn.commit()
    conn.close()

def get_vault_meta():
    conn = get_db()
    row  = conn.execute("SELECT * FROM vault_meta").fetchone()
    conn.close()
    return dict(row) if row else {}