"""
vault.py
Handles saving and loading the encrypted vault file from disk.
"""

import os
from honey_encryption import encrypt_vault, decrypt_vault

VAULT_FILE = 'honeyvault.enc'

def vault_exists() -> bool:
    return os.path.exists(VAULT_FILE)

def save_vault(entries: list, master_password: str):
    """Encrypt and save vault to disk."""
    encrypted = encrypt_vault(entries, master_password)
    with open(VAULT_FILE, 'wb') as f:
        f.write(encrypted)

def load_vault(master_password: str) -> tuple:
    """
    Load and decrypt vault from disk.
    Returns (entries, is_real).
    """
    if not vault_exists():
        return [], False
    with open(VAULT_FILE, 'rb') as f:
        data = f.read()
    return decrypt_vault(data, master_password)