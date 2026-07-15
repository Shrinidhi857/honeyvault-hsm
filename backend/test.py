# test.py
from honey_encryption import encrypt_vault, decrypt_vault

real_entries = [
    {'id':1,'site':'gmail.com','username':'john@gmail.com','password':'MyR3alP@ss!','notes':'','created':'2023-01-01','canary':''},
    {'id':2,'site':'github.com','username':'john_dev','password':'G1tHub#Secret','notes':'Work','created':'2023-03-15','canary':''},
]

# Encrypt
enc = encrypt_vault(real_entries, "CorrectHorseBattery")
print(f"Encrypted: {len(enc)} bytes")

# Decrypt with correct password
entries, is_real = decrypt_vault(enc, "CorrectHorseBattery")
print(f"Correct pwd -> is_real={is_real}, entries={len(entries)}")
print(f"  First entry: {entries[0]['site']} / {entries[0]['username']}")

# Decrypt with wrong password
entries, is_real = decrypt_vault(enc, "wrongpassword123")
print(f"Wrong pwd  -> is_real={is_real}, entries={len(entries)}")
print(f"  First entry: {entries[0]['site']} / {entries[0]['username']}")