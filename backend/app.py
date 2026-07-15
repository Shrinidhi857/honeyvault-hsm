"""
app.py
HoneyVault Flask REST API  --  Zero-Knowledge Hardware Architecture

Features
- Physical Presence Gate (GPIO 17 button) blocks unlock requests until
  the physical button on the Pi is pressed within BUTTON_TIMEOUT seconds.
- DTE Honey Encryption (AES-256-CTR) with Canary Tracker
- Offline brute-force simulation (Classic AES-CBC vs DTE)
- Serves compiled React SPA from frontend/dist/ in production
"""

import os
import datetime
from flask import Flask, request, jsonify, session, Response, send_from_directory
from flask_cors import CORS

from vault import save_vault, load_vault, vault_exists
from database import (
    init_db, log_canary_hit, get_canary_hits,
    log_action, get_audit_log,
    create_vault_meta, update_vault_meta, get_vault_meta,
)
from hardware import wait_for_button_press, press_mock_button, HAS_GPIO

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

LOCAL_DIST = os.path.join(os.path.dirname(__file__), 'dist')
PARENT_DIST = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')

if os.path.isdir(LOCAL_DIST):
    FRONTEND_DIST = LOCAL_DIST
elif os.path.isdir(PARENT_DIST):
    FRONTEND_DIST = PARENT_DIST
else:
    FRONTEND_DIST = None

app = Flask(
    __name__,
    static_folder=FRONTEND_DIST,
    static_url_path='',
)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

CORS(app, supports_credentials=True, origins=[
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:5000',
])

BUTTON_TIMEOUT = 10   # seconds the user has to press the physical button

# ---------------------------------------------------------------------------
# SPA catch-all  (serves index.html for non-API routes in production build)
# ---------------------------------------------------------------------------

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path):
    if path.startswith('api') or path == 'canary':
        return jsonify(error='Not found'), 404
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    index_html = os.path.join(FRONTEND_DIST, 'index.html')
    if os.path.exists(index_html):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return jsonify(
        status='HoneyVault API Running',
        mode='development',
        hint='Start the React dev server at localhost:5173 or run npm run build',
    ), 200

# ---------------------------------------------------------------------------
# Hardware gate endpoints
# ---------------------------------------------------------------------------

@app.get('/api/hardware/status')
def hardware_status():
    return jsonify(
        gpio_available=HAS_GPIO,
        button_pin=17,
        mode='HARDWARE' if HAS_GPIO else 'SIMULATED',
        timeout_seconds=BUTTON_TIMEOUT,
    )

@app.post('/api/demo/press-button')
def simulate_button():
    """PC testing only -- simulate a physical GPIO button press."""
    press_mock_button()
    return jsonify(status='pressed', message='Mock hardware button press triggered.')

# ---------------------------------------------------------------------------
# Vault routes
# ---------------------------------------------------------------------------

@app.post('/api/vault/create')
def create_vault():
    d               = request.json or {}
    master_password = d.get('master_password', '')
    entries         = d.get('entries', [])

    if not master_password or len(master_password) < 8:
        return jsonify(error='Master password must be at least 8 characters.'), 400
    if len(entries) > 10:
        return jsonify(error='Vault is limited to 10 slots in this PoC.'), 400
    if vault_exists():
        return jsonify(error='Vault already exists. Use /api/vault/unlock.'), 400

    save_vault(entries, master_password)
    create_vault_meta()
    log_action('VAULT_CREATED', f'{len(entries)} entries', request.remote_addr)
    session['unlocked']        = True
    session['is_real']         = True
    session['entries']         = entries
    session['master_password'] = master_password
    return jsonify(status='created', entries=len(entries))


@app.post('/api/vault/unlock')
def unlock_vault():
    """
    Unlock the vault with Physical Presence Gate.

    Flow:
      1. Verify vault exists.
      2. Block up to BUTTON_TIMEOUT seconds waiting for a hardware button press.
      3. If confirmed -> decrypt vault, return entries (real OR decoy).
      4. If timeout   -> 403, gate_timeout=True.
    """
    d               = request.json or {}
    master_password = d.get('master_password', '')

    if not vault_exists():
        return jsonify(error='No vault found. Create one first.'), 404

    # Physical Presence Gate
    confirmed = wait_for_button_press(timeout=BUTTON_TIMEOUT)
    if not confirmed:
        log_action('GATE_TIMEOUT', 'No button press within window', request.remote_addr)
        return jsonify(
            error='Physical hardware confirmation timed out.',
            gate_timeout=True,
        ), 403

    # Decrypt
    entries, is_real = load_vault(master_password)

    session['unlocked']        = True
    session['is_real']         = is_real
    session['entries']         = entries
    session['master_password'] = master_password

    if is_real:
        update_vault_meta(True)
        log_action('VAULT_UNLOCKED', 'Correct password + hardware confirmed', request.remote_addr)
        return jsonify(entries=entries, is_real=True)
    else:
        update_vault_meta(False)
        log_action('FAILED_UNLOCK', 'Wrong password (decoy served after gate passed)', request.remote_addr)
        log_canary_hit(
            ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            password_used=master_password,
            ref='vault_unlock',
        )
        return jsonify(entries=entries, is_real=False)


@app.get('/api/vault/raw')
def vault_raw():
    if not vault_exists():
        return jsonify(error='No vault found.'), 404
    with open('honeyvault.enc', 'rb') as f:
        data = f.read()
    hex_lines = []
    for i in range(0, min(128, len(data)), 16):
        chunk    = data[i:i + 16]
        hex_part = ' '.join(f'{b:02X}' for b in chunk)
        hex_lines.append(f'{i:04X}  {hex_part}')
    return jsonify(
        size_bytes=len(data),
        hex_preview='\n'.join(hex_lines),
        algorithm='AES-256-CTR',
        kdf='PBKDF2-SHA256',
        iterations=200_000,
    )


@app.get('/api/vault/entries')
def get_entries():
    if not session.get('unlocked'):
        return jsonify(error='Vault is locked.'), 401
    return jsonify(
        entries=session.get('entries', []),
        is_real=session.get('is_real', False),
    )


@app.post('/api/vault/add')
def add_entry():
    if not session.get('unlocked'):
        return jsonify(error='Vault is locked.'), 401
    if not session.get('is_real'):
        return jsonify(status='added', message='Entry saved.')
    d       = request.json or {}
    entries = session.get('entries', [])
    if len(entries) >= 10:
        return jsonify(error='Vault limited to 10 slots in this PoC.'), 400
    new_entry = {
        'id':       len(entries) + 1,
        'site':     d.get('site', ''),
        'username': d.get('username', ''),
        'password': d.get('password', ''),
        'notes':    d.get('notes', ''),
        'created':  datetime.date.today().strftime('%Y-%m-%d'),
        'canary':   '',
    }
    entries.append(new_entry)
    session['entries'] = entries
    save_vault(entries, session.get('master_password', ''))
    return jsonify(status='added', entry=new_entry)


@app.post('/api/vault/lock')
def lock_vault():
    session.clear()
    return jsonify(status='locked')


@app.get('/api/vault/status')
def vault_status():
    return jsonify(
        vault_exists=vault_exists(),
        unlocked=session.get('unlocked', False),
        is_real=session.get('is_real', False),
    )


# ---------------------------------------------------------------------------
# Brute-force demo  (no hardware gate -- simulation only)
# ---------------------------------------------------------------------------

@app.post('/api/demo/attack')
def demo_attack():
    pwd = (request.json or {}).get('password', '')
    if not vault_exists():
        return jsonify(error='No vault to attack. Create one first.'), 404
    entries, is_real = load_vault(pwd)
    if not is_real:
        log_canary_hit(
            ip=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            password_used=pwd,
            ref='brute_force_demo',
        )
    return jsonify(is_real=is_real, entries=entries, password_tried=pwd, total=len(entries))


@app.post('/api/demo/offline-attack')
def offline_attack_demo():
    import json as _j, time as _t
    from Crypto.Cipher import AES as _AES
    from Crypto.Protocol.KDF import PBKDF2 as _KDF
    from Crypto.Random import get_random_bytes as _rnd
    from Crypto.Util.Padding import pad as _pad, unpad as _unpad
    from honey_encryption import decrypt_vault as _dec

    data          = request.json or {}
    wordlist      = data.get('wordlist', ['password','123456','admin','letmein','qwerty',
                                          'dragon','iloveyou','monkey','master','batman'])
    real_password = data.get('real_password', '')

    demo_entries = [
        {'site':'google.com','username':'demo@google.com','password':'Demo!Pass99','notes':''},
        {'site':'github.com','username':'demo_dev',       'password':'G1t#Demo99', 'notes':''},
    ]
    classic_pwd = real_password or 'SecretNotInList!99'
    s1 = _rnd(16); i1 = _rnd(16)
    k1 = _KDF(classic_pwd.encode(), s1, dkLen=32, count=200_000)
    ct = _AES.new(k1, _AES.MODE_CBC, i1).encrypt(_pad(_j.dumps(demo_entries).encode(), _AES.block_size))
    blob = s1 + i1 + ct

    phase1 = []
    for g in wordlist:
        t0 = _t.perf_counter()
        k  = _KDF(g.encode(), blob[:16], dkLen=32, count=200_000)
        try:
            _j.loads(_unpad(_AES.new(k, _AES.MODE_CBC, blob[16:32]).decrypt(blob[32:]), _AES.block_size).decode())
            cracked = True
        except Exception:
            cracked = False
        phase1.append({'password':g,'cracked':cracked,
                        'result':'CRACKED' if cracked else 'INVALID_PADDING',
                        'time_s':round(_t.perf_counter()-t0,3)})

    if not vault_exists():
        return jsonify(error='No vault found. Create one first.'), 404
    with open('honeyvault.enc','rb') as f:
        dte = f.read()
    phase2 = []
    for g in wordlist:
        t0 = _t.perf_counter()
        ents, ir = _dec(dte, g)
        s = ents[0] if ents else {}
        phase2.append({'password':g,'cracked':False,'is_real':ir,'result':'REAL' if ir else 'DECOY',
                        'entries':len(ents),'sample_site':s.get('site',''),'sample_user':s.get('username','')[:28],
                        'time_s':round(_t.perf_counter()-t0,3)})

    return jsonify(phase1=phase1, phase2=phase2, vault_size=len(dte))


@app.post('/api/demo/offline-attack/guess')
def offline_attack_guess():
    import json as _j, time as _t, hashlib as _h
    from Crypto.Cipher import AES as _AES
    from Crypto.Protocol.KDF import PBKDF2 as _KDF
    from Crypto.Util.Padding import pad as _pad, unpad as _unpad
    from honey_encryption import decrypt_vault as _dec

    d             = request.json or {}
    guess         = d.get('password', '')
    real_password = d.get('real_password', '')

    demo_entries = [
        {'site':'google.com','username':'demo@google.com','password':'Demo!Pass99','notes':''},
        {'site':'github.com','username':'demo_dev',       'password':'G1t#Demo99', 'notes':''},
    ]
    classic_pwd = real_password or 'SecretNotInList!99'
    ph  = _h.sha256(classic_pwd.encode()).digest()
    s1 = ph[:16]; i1 = ph[16:32]
    k1 = _KDF(classic_pwd.encode(), s1, dkLen=32, count=200_000)
    ct = _AES.new(k1, _AES.MODE_CBC, i1).encrypt(_pad(_j.dumps(demo_entries).encode(), _AES.block_size))
    blob = s1 + i1 + ct

    t0 = _t.perf_counter()
    k  = _KDF(guess.encode(), blob[:16], dkLen=32, count=200_000)
    try:
        _j.loads(_unpad(_AES.new(k, _AES.MODE_CBC, blob[16:32]).decrypt(blob[32:]), _AES.block_size).decode())
        cracked = True
    except Exception:
        cracked = False
    aes_result = {'cracked':cracked,'result':'CRACKED' if cracked else 'INVALID_PADDING','time_s':round(_t.perf_counter()-t0,3)}

    if not vault_exists():
        return jsonify(error='No vault found.'), 404
    with open('honeyvault.enc','rb') as f:
        dte = f.read()
    t0 = _t.perf_counter()
    entries, is_real = _dec(dte, guess)
    sample = entries[0] if entries else {}

    attacker_analysis = {
        'aes_heading':  'Real Password Entered'  if is_real else 'Invalid Padding',
        'aes':          'Correct password - actual credentials decrypted.' if is_real
                        else 'Wrong key produced garbage. PKCS7 padding FAILED. Attacker discards instantly.',
        'honey_heading':'Real Password Entered'  if is_real else 'Valid Vault Produced',
        'honey':        'Correct password - authentic database returned.' if is_real
                        else 'Wrong key -> random bytes -> DTE maps to plausible credentials. No error. Attacker cannot distinguish.',
    }
    honey_result = {
        'is_real':is_real,'result':'REAL' if is_real else 'DECOY',
        'entries':len(entries),'sample_site':sample.get('site',''),
        'sample_user':sample.get('username','')[:28],'sample_pass':sample.get('password',''),
        'time_s':round(_t.perf_counter()-t0,3),'entries_list':entries,
    }
    return jsonify(password=guess, aes_result=aes_result, honey_result=honey_result, attacker_analysis=attacker_analysis)


# ---------------------------------------------------------------------------
# Canary beacon + admin routes
# ---------------------------------------------------------------------------

@app.get('/canary')
def canary():
    ref = request.args.get('ref', 'unknown')
    log_canary_hit(
        ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent', ''),
        password_used='beacon_triggered',
        ref=f'CANARY_BEACON ref={ref}',
    )
    pixel = (
        b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00'
        b'\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00'
        b'\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    )
    return Response(pixel, mimetype='image/gif')

@app.get('/api/canary/hits')
def canary_hits():
    return jsonify(hits=get_canary_hits())

@app.get('/api/audit/log')
def audit_log():
    return jsonify(log=get_audit_log())

@app.get('/api/vault/meta')
def vault_meta():
    return jsonify(meta=get_vault_meta())

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    mode = 'REAL GPIO (Raspberry Pi)' if HAS_GPIO else 'SIMULATED (PC / Dev Mode)'
    print('HoneyVault backend starting...')
    print(f'Hardware Mode: {mode}')
    print('API: http://localhost:5000')
    app.run(debug=True, port=5000, threaded=True)
