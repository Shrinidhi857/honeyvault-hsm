"""
honey_encryption.py
True DTE (Distribution Transforming Encoder) Honey Encryption implementation for HoneyVault.
"""

import hashlib
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

SALT_SIZE = 16
KEY_SIZE  = 32   # AES-256
IV_SIZE   = 8    # AES-CTR uses 8-byte nonce by default in PyCryptodome

# ── DTE Configuration ─────────────────────────────────────────────────────────

# Token vocabulary for DTE. Index 0 is the null padding character.
TOKENS = [
    # Padding / Null (1 total)
    "\x00",
    # Individual characters (71 total)
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", 
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", 
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    ".", "@", "!", "_", "-", "#", "*", " ", "+", "=",
    
    # Syllables (56 total)
    "ba", "be", "bi", "bo", "bu",
    "ca", "ce", "ci", "co", "cu",
    "da", "de", "di", "do", "du",
    "fa", "fe", "fi", "fo", "fu",
    "ga", "ge", "gi", "go", "gu",
    "ha", "he", "hi", "ho", "hu",
    "la", "le", "li", "lo", "lu",
    "ma", "me", "mi", "mo", "mu",
    "na", "ne", "ni", "no", "nu",
    "ra", "re", "ri", "ro", "ru",
    "sa", "se", "si", "so", "su",
    "ta", "te", "ti", "to", "tu", "va"
]

POPULAR_SITES = [
    "google.com", "facebook.com", "youtube.com", "yahoo.com", "amazon.com",
    "wikipedia.org", "twitter.com", "netflix.com", "github.com", "linkedin.com",
    "reddit.com", "instagram.com", "microsoft.com", "apple.com", "pinterest.com",
    "paypal.com", "ebay.com", "wordpress.com", "tumblr.com", "imgur.com",
    "stackoverflow.com", "imdb.com", "office.com", "adobe.com", "spotify.com"
]

POPULAR_USERNAMES = [
    "admin", "support", "info", "user", "contact", "hello", "john.doe",
    "jane.smith", "test.user", "owner", "administrator", "webmaster",
    "sales", "jobs", "billing", "service", "staff", "office"
]

# ── Helper Functions for DTE ──────────────────────────────────────────────────

def tokenize_string(s: str) -> list:
    """Greedily tokenize a string using our 128-token list."""
    tokens = []
    i = 0
    # Sort TOKENS by length descending so we match syllables first
    sorted_tokens = sorted([(t, idx) for idx, t in enumerate(TOKENS) if len(t) > 0], key=lambda x: len(x[0]), reverse=True)
    
    while i < len(s):
        matched = False
        for t, idx in sorted_tokens:
            if s.startswith(t, i):
                tokens.append(t)
                i += len(t)
                matched = True
                break
        if not matched:
            i += 1  # Skip unrecognized chars to prevent infinite loop
    return tokens

def tokens_to_bits(tokens: list, max_tokens: int) -> int:
    """Pack a list of tokens into a single integer representing a bitstring."""
    val = 0
    t_list = tokens[:max_tokens]
    # Pad to max_tokens using index 0 (which is "\x00")
    while len(t_list) < max_tokens:
        t_list.append("\x00")
    
    token_to_idx = {t: idx for idx, t in enumerate(TOKENS)}
    for t in reversed(t_list):
        idx = token_to_idx.get(t, 0)
        val = (val << 7) | idx
    return val

def bits_to_tokens(val: int, max_tokens: int) -> list:
    """Unpack a bitstring integer back into a list of tokens."""
    tokens = []
    for _ in range(max_tokens):
        idx = val & 0x7F
        tokens.append(TOKENS[idx])
        val >>= 7
    return tokens


# ── Decoy Field Sanitizers ───────────────────────────────────────────────────

import re as _re

_SITE_SAFE    = _re.compile(r'[^a-zA-Z0-9.-]')
_USER_SAFE    = _re.compile(r'[^a-zA-Z0-9.@_-]')
_SITE_TLDS    = ["com", "net", "org", "io", "co"]

def _sanitize_site(raw: str) -> str:
    """Strip symbols from a DTE-decoded site. Result always ends with .com (or similar TLD)."""
    clean = _SITE_SAFE.sub('', raw)          # keep only letters, digits, dots, hyphens
    clean = clean.strip('.-')                # trim leading/trailing dots and hyphens
    # Ensure there is at least a stub domain
    if len(clean) < 3:
        clean = "vault" + clean
    # Ensure the site has a TLD-looking suffix
    if '.' not in clean:
        # Use a deterministic TLD based on the string itself
        clean = clean + '.' + _SITE_TLDS[len(clean) % len(_SITE_TLDS)]
    return clean.lower()

def _sanitize_username(raw: str, site: str) -> str:
    """Strip symbols from a DTE-decoded username."""
    clean = _USER_SAFE.sub('', raw).strip('.@_-')
    if len(clean) < 2:
        clean = "user" + clean
    # If no @ present, append @site for realism
    if '@' not in clean:
        clean = clean + '@' + site
    return clean.lower()

def _sanitize_password(raw: str) -> str:
    """Strip null bytes and replace spaces from a DTE-decoded password."""
    return raw.replace('\x00', '').replace(' ', '').strip() or "Decoy1!"


# ── Key Derivation ───────────────────────────────────────────────────────────

def derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-SHA256 with 200,000 iterations."""
    return PBKDF2(password.encode(), salt, dkLen=KEY_SIZE, count=200_000)

# ── Entry Encoder and Decoder ─────────────────────────────────────────────────

def encode_entry(entry: dict, is_active: bool = True) -> bytes:
    """Encode a vault entry into exactly 47 bytes."""
    site     = entry.get('site', '')
    username = entry.get('username', '')
    password = entry.get('password', '')
    notes    = entry.get('notes', '')

    flag = 0x00
    if is_active:
        flag |= 0x01

    # Encode site
    if site in POPULAR_SITES:
        flag |= 0x80
        site_val = POPULAR_SITES.index(site)
    else:
        site_val = tokens_to_bits(tokenize_string(site), 12)

    # Encode username
    base_user = username
    if "@" in username:
        parts = username.split("@", 1)
        base_user = parts[0]
    
    if base_user in POPULAR_USERNAMES:
        flag |= 0x40
        user_val = POPULAR_USERNAMES.index(base_user)
    else:
        user_val = tokens_to_bits(tokenize_string(username), 14)

    # Encode password
    if password.startswith("Secr!t") and len(password) == 10 and password[6:].isdigit():
        flag |= 0x20
        pass_val = int(password[6:])
    else:
        pass_val = tokens_to_bits(tokenize_string(password), 14)

    # Encode notes
    notes_options = ["Personal account", "Work login", "Mock account"]
    if notes in notes_options:
        flag |= 0x10
        notes_val = notes_options.index(notes)
    else:
        notes_val = tokens_to_bits(tokenize_string(notes), 7)

    # Convert to a fixed byte format
    res = bytearray(47)
    res[0] = flag
    res[1:12] = site_val.to_bytes(11, 'little')
    res[12:26] = user_val.to_bytes(14, 'little')
    res[26:40] = pass_val.to_bytes(14, 'little')
    res[40:47] = notes_val.to_bytes(7, 'little')
    return bytes(res)

def decode_entry(data_bytes: bytes, index: int) -> dict:
    """Decode 47 bytes back into a vault entry dict."""
    flag = data_bytes[0]
    site_val = int.from_bytes(data_bytes[1:12], 'little')
    user_val = int.from_bytes(data_bytes[12:26], 'little')
    pass_val = int.from_bytes(data_bytes[26:40], 'little')
    notes_val = int.from_bytes(data_bytes[40:47], 'little')

    # Decode site
    if flag & 0x80:
        site = POPULAR_SITES[site_val % len(POPULAR_SITES)]
    else:
        raw_site = "".join(bits_to_tokens(site_val, 12)).rstrip("\x00")
        site = _sanitize_site(raw_site)

    # Decode username
    if flag & 0x40:
        base_user = POPULAR_USERNAMES[user_val % len(POPULAR_USERNAMES)]
        username = f"{base_user}@{site}"
    else:
        raw_user = "".join(bits_to_tokens(user_val, 14)).rstrip("\x00")
        username = _sanitize_username(raw_user, site)

    # Decode password
    if flag & 0x20:
        password = f"Secr!t{(pass_val % 10000):04d}"
    else:
        raw_pass = "".join(bits_to_tokens(pass_val, 14)).rstrip("\x00")
        password = _sanitize_password(raw_pass)

    # Decode notes
    if flag & 0x10:
        notes_options = ["Personal account", "Work login", "Mock account"]
        notes = notes_options[notes_val % len(notes_options)]
    else:
        notes = "".join(bits_to_tokens(notes_val, 7)).rstrip("\x00")

    return {
        'id': index + 1,
        'site': site,
        'username': username,
        'password': password,
        'notes': notes,
        'created': '2026-07-05',
        'canary': '',
        'is_active': bool(flag & 0x01)
    }

def generate_mock_entry(i: int) -> dict:
    """Generate a deterministic mock entry to pad the vault."""
    site = POPULAR_SITES[i % len(POPULAR_SITES)]
    username = f"user{i}@{site}"
    password = f"MockPassword{i}!"
    notes = "Mock account"
    return {
        'site': site,
        'username': username,
        'password': password,
        'notes': notes
    }

# ── Encrypt / Decrypt ─────────────────────────────────────────────────────────

def encrypt_vault(entries: list, master_password: str) -> bytes:
    """
    Encrypts the real vault entries with AES-256-CTR.
    Uses fixed 480-byte size.
    """
    payload = bytearray(480)
    # Magic header: first 4 bytes. Used for local validation of correct decryption.
    # NOTE: In a production Honey Encryption system, we would not use a signature
    # because an offline attacker could verify it. We include it here to enable
    # the frontend UI to display the "REAL" vs "DECOY" badge.
    payload[0:4] = b'HNYV'

    # Populate real entries
    for i, entry in enumerate(entries[:10]):
        offset = 8 + i * 47
        payload[offset:offset+47] = encode_entry(entry, is_active=True)

    # Pad remaining entries with mock entries
    for i in range(len(entries), 10):
        offset = 8 + i * 47
        mock = generate_mock_entry(i)
        payload[offset:offset+47] = encode_entry(mock, is_active=False)

    salt = get_random_bytes(SALT_SIZE)
    nonce = get_random_bytes(IV_SIZE)
    key = derive_key(master_password, salt)

    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    ciphertext = cipher.encrypt(bytes(payload))

    return salt + nonce + ciphertext

def decrypt_vault(data: bytes, master_password: str) -> tuple:
    """
    Decrypts the vault. Never fails with decryption errors.
    Returns (entries, is_real).
    """
    if len(data) < SALT_SIZE + IV_SIZE + 480:
        # File is corrupted or too short
        return [], False

    salt = data[:SALT_SIZE]
    nonce = data[SALT_SIZE : SALT_SIZE + IV_SIZE]
    ciphertext = data[SALT_SIZE + IV_SIZE : SALT_SIZE + IV_SIZE + 480]

    key = derive_key(master_password, salt)
    cipher = AES.new(key, AES.MODE_CTR, nonce=nonce)
    payload = cipher.decrypt(ciphertext)

    # Check magic signature
    is_real = (payload[0:4] == b'HNYV')

    entries = []
    if is_real:
        # Decrypted successfully with the correct password. Only return active entries.
        for i in range(10):
            offset = 8 + i * 47
            entry = decode_entry(payload[offset:offset+47], i)
            if entry['is_active']:
                # Strip internal helper key before returning
                del entry['is_active']
                entries.append(entry)
        return entries, True
    else:
        # Wrong password! Decrypted random bytes decode to plausible decoy entries.
        for i in range(10):
            offset = 8 + i * 47
            entry = decode_entry(payload[offset:offset+47], i)
            del entry['is_active']
            if i == 0:
                # Embed canary URL in first entry
                seed_int = int(hashlib.md5(payload).hexdigest(), 16) % (2 ** 31)
                entry['canary'] = f"http://localhost:5000/canary?ref={seed_int}&src=vault"
            entries.append(entry)
        return entries, False