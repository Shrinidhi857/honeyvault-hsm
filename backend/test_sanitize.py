import os
from honey_encryption import decrypt_vault

VAULT = 'honeyvault.enc'
if not os.path.exists(VAULT):
    print('No vault file found')
else:
    data = open(VAULT, 'rb').read()
    entries, is_real = decrypt_vault(data, 'dragon')
    print('is_real:', is_real, '|', len(entries), 'entries')
    for e in entries[:5]:
        print('  site:', e['site'], ' | user:', e['username'], ' | pass:', e['password'])
