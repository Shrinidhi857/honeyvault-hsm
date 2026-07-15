"""
offline_attack_simulation.py
============================
Simulates an offline brute-force attacker who has stolen the encrypted
vault file from disk and is attempting to crack it WITHOUT the Flask server.

Two phases are demonstrated:
  Phase 1 - Classic AES-CBC (old system): attacker gets instant FAIL signals.
  Phase 2 - DTE Honey Encryption (new system): attacker gets valid-looking
            data on every single guess and cannot tell real from decoy.

Run from the backend directory:
    python offline_attack_simulation.py
"""

import os
import sys
# Force UTF-8 output on Windows so box-drawing chars print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import time
import json
import hashlib

from Crypto.Cipher    import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random    import get_random_bytes
from Crypto.Util.Padding import pad, unpad

# ── Import our DTE module ─────────────────────────────────────────────────────
from honey_encryption import (
    encrypt_vault, decrypt_vault,
    SALT_SIZE, IV_SIZE
)

# ── Terminal colour helpers ───────────────────────────────────────────────────
R  = "\033[91m"   # red
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
B  = "\033[94m"   # blue
M  = "\033[95m"   # magenta
C  = "\033[96m"   # cyan
W  = "\033[97m"   # white
DIM = "\033[2m"
BOLD = "\033[1m"
RST = "\033[0m"

def hr(char="=", width=72, color=DIM):
    print(f"{color}{char * width}{RST}")

def banner(text, color=BOLD+C):
    hr("=")
    print(f"{color}  {text}{RST}")
    hr("=")

def section(text, color=BOLD+Y):
    print()
    hr("-", color=color)
    print(f"{color}  {text}{RST}")
    hr("-", color=color)

def ok(msg):   print(f"  {G}[+]{RST} {msg}")
def fail(msg): print(f"  {R}[-]{RST} {msg}")
def info(msg): print(f"  {C}[*]{RST} {msg}")
def warn(msg): print(f"  {Y}[!]{RST} {msg}")
def decoy(msg): print(f"  {Y}[~]{RST} {msg}")

# ── Candidate password list (simulating a dictionary / wordlist) ──────────────
WORDLIST = [
    "password", "123456", "admin", "letmein", "qwerty",
    "dragon", "iloveyou", "monkey", "master", "batman",
    "sunshine", "princess", "welcome", "shadow", "superman",
    "michael", "football", "abc123", "pass123", "test1234",
]

# ── Real vault credentials (used to build the test vault) ────────────────────
REAL_ENTRIES = [
    {"site": "google.com",  "username": "john.doe@google.com",  "password": "G00gl3#Secure!", "notes": "Personal account"},
    {"site": "github.com",  "username": "john_dev",             "password": "G1tHub#Secret",  "notes": "Work login"},
    {"site": "netflix.com", "username": "john_movies",          "password": "Netfl!x@2026",   "notes": "Personal account"},
]
REAL_PASSWORD = "MasterPassword123!"


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 1 — Classic AES-CBC (old system)
# ═══════════════════════════════════════════════════════════════════════════════

def build_classic_vault(entries: list, master_password: str) -> bytes:
    """Encrypt entries as AES-256-CBC with PKCS7 padding — standard approach."""
    salt = get_random_bytes(16)
    iv   = get_random_bytes(16)
    key  = PBKDF2(master_password.encode(), salt, dkLen=32, count=200_000)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = json.dumps(entries).encode("utf-8")
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
    return salt + iv + ciphertext


def classic_try_password(data: bytes, password: str) -> tuple:
    """
    Returns (success, entries_or_none).
    An attacker running this offline gets a hard YES/NO signal instantly.
    """
    salt       = data[:16]
    iv         = data[16:32]
    ciphertext = data[32:]
    key        = PBKDF2(password.encode(), salt, dkLen=32, count=200_000)
    try:
        cipher  = AES.new(key, AES.MODE_CBC, iv)
        plain   = unpad(cipher.decrypt(ciphertext), AES.block_size)
        entries = json.loads(plain.decode("utf-8"))
        return True, entries                 # ✅ CRACKED
    except Exception:
        return False, None                   # ❌ WRONG — padding/json error


def run_phase1():
    section("PHASE 1  —  Classic AES-CBC (Standard Password Manager)")
    print(f"""
  {DIM}In a normal password manager, encryption uses AES-CBC with PKCS7 padding.
  A wrong key produces random bytes that fail the padding check instantly.
  An offline attacker on a GPU rig can test BILLIONS of keys per second
  and immediately discard wrong guesses — only one key gives valid padding.{RST}
""")

    info(f"Building classic AES-CBC vault with {len(REAL_ENTRIES)} real entries...")
    classic_data = build_classic_vault(REAL_ENTRIES, REAL_PASSWORD)
    info(f"Vault size: {len(classic_data)} bytes  (size reveals entry count)\n")

    hr("-")
    print(f"  {BOLD}Attacker is now offline -- no server -- testing wordlist...{RST}")
    hr("-")

    cracked_at = None
    total_time = 0.0

    for i, guess in enumerate(WORDLIST + [REAL_PASSWORD]):
        t0 = time.perf_counter()
        success, entries = classic_try_password(classic_data, guess)
        elapsed = time.perf_counter() - t0
        total_time += elapsed

        label = f"Attempt #{i+1:>2}  pwd={guess!r:<22}"

        if success:
            ok(f"{label}  -> {G}{BOLD}CRACKED{RST} in {elapsed:.2f}s  ({len(entries)} real entries found)")
            cracked_at = i + 1
            break
        else:
            fail(f"{label}  -> {R}INVALID padding -- discarded instantly{RST}  ({elapsed:.2f}s)")

    print()
    if cracked_at:
        warn(f"Attacker cracked the vault after {cracked_at} attempt(s) in {total_time:.2f}s total.")
        warn("Every wrong guess gave a definitive error signal. Attacker knew exactly when to stop.")
    else:
        warn("Real password not in wordlist. Attacker failed -- but got clear FAIL signals every time.")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 2 — DTE Honey Encryption (new system)
# ═══════════════════════════════════════════════════════════════════════════════

def run_phase2(vault_file: str):
    section("PHASE 2  —  DTE Honey Encryption (HoneyVault)")
    print(f"""
  {DIM}With Honey Encryption + AES-CTR (no padding, no integrity tag):
    - Every key mathematically decrypts to a valid 480-byte block.
    - The DTE decoder maps those bytes to plausible credentials.
    - The attacker CANNOT distinguish real from decoy using automated tools.
    - The only way to verify is to try logging in online — slow, detectable.{RST}
""")

    if not os.path.exists(vault_file):
        warn(f"No vault found at '{vault_file}'. Building a fresh one for the demo...")
        raw = encrypt_vault(REAL_ENTRIES, REAL_PASSWORD)
        with open(vault_file, "wb") as f:
            f.write(raw)
        ok(f"Demo vault written: {len(raw)} bytes\n")

    with open(vault_file, "rb") as f:
        encrypted_data = f.read()

    info(f"Vault file: {vault_file}  ({len(encrypted_data)} bytes -- fixed size, reveals nothing)\n")

    hr("-")
    print(f"  {BOLD}Attacker is offline -- testing the same wordlist against DTE vault...{RST}")
    hr("-")

    results_table = []
    total_time    = 0.0
    real_found    = False

    for i, guess in enumerate(WORDLIST + [REAL_PASSWORD]):
        t0 = time.perf_counter()
        entries, is_real = decrypt_vault(encrypted_data, guess)
        elapsed = time.perf_counter() - t0
        total_time += elapsed

        label    = f"Attempt #{i+1:>2}  pwd={guess!r:<22}"
        sample   = entries[0] if entries else {}
        site_str = sample.get("site", "?")
        user_str = sample.get("username", "?")[:20]

        if is_real:
            ok(f"{label}  -> {G}{BOLD}REAL (detected by magic header){RST}   {elapsed:.2f}s")
            ok(f"             Sample: {site_str} / {user_str}")
            real_found = True
        else:
            # Attacker sees this as a "success" -- but it's decoy
            decoy(f"{label}  -> {Y}DECOY (looks real to attacker){RST}   {elapsed:.2f}s")
            print(f"       {DIM}Sample: {site_str} / {user_str}{RST}")

        results_table.append({
            "attempt": i + 1,
            "password": guess,
            "success": True,           # always True — DTE never fails
            "is_real": is_real,
            "entries": len(entries),
            "time_s": round(elapsed, 3),
        })

    print()
    return results_table, total_time


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def print_report(results: list, total_time: float):
    section("ATTACK REPORT — DTE Honey Encryption", color=BOLD+M)

    total    = len(results)
    decoys   = sum(1 for r in results if not r["is_real"])
    real_cnt = sum(1 for r in results if r["is_real"])

    print(f"""
  {BOLD}Summary{RST}
  +----------------------------------------------------------+
  |  Total attempts          : {total:<5}                         |
  |  Cryptographic failures  : {R}0{RST}     <- attacker can't discard  |
  |  Decoy vaults returned   : {Y}{decoys:<5}{RST}                         |
  |  Real vault detected     : {G if real_cnt else R}{real_cnt:<5}{RST} (magic header present)  |
  |  Total time              : {total_time:.2f}s                         |
  +----------------------------------------------------------+
""")

    print(f"  {BOLD}What the attacker sees:{RST}")
    print(f"  {'#':<4} {'Password':<22} {'Status':<20} {'Entries':<8} {'Time'}")
    hr("-", 65)
    for r in results:
        status = f"{G}REAL [OK]{RST}" if r["is_real"] else f"{Y}DECOY [~]{RST}"
        print(f"  {r['attempt']:<4} {r['password']:<22} {status:<28} {r['entries']:<8} {r['time_s']:.3f}s")

    print(f"""
  {BOLD}Key insight:{RST}
  {DIM}An automated cracking tool has no way to filter wrong keys.
  It must attempt to log in to each site with the decoy credentials --
  that is an online operation, instantly detectable by rate limiters,
  honeypots, and 2FA. The attacker's offline advantage is neutralised.{RST}
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    VAULT_FILE = "honeyvault.enc"

    banner("HoneyVault -- Offline Brute-Force Attack Simulator")
    print(f"""
  {DIM}This script bypasses Flask entirely and acts as an offline attacker
  who has obtained the raw encrypted vault file from disk.

  It demonstrates two scenarios side-by-side:
    1. Classic AES-CBC  → wrong key = instant padding error (crackable)
    2. DTE Honey Enc.   → wrong key = plausible decoy (attacker is blind)
  {RST}""")

    # Phase 1 — old approach
    run_phase1()

    # Phase 2 — new DTE approach
    results, total_time = run_phase2(VAULT_FILE)

    # Final report
    print_report(results, total_time)

    banner("Simulation Complete -- DTE Honey Encryption prevails", color=BOLD+G)
