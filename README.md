# 🍯 HoneyVault: DTE Honey Encryption Password Manager (PoC)

HoneyVault is a security-focused proof-of-concept (PoC) password manager that implements **Honey Encryption with a custom Distribution Transforming Encoder (DTE)** to protect against offline brute-force attacks. 

---

## 📖 Table of Contents
1. [Theoretical Concept & DTE Mechanics](#-theoretical-concept--dte-mechanics)
2. [Core Features & Detailed How It Works Guide](#-core-features--detailed-how-it-works-guide)
3. [Architecture Overview](#-architecture-overview)
4. [Backend Code & Function Reference](#-backend-code--function-reference)
5. [Frontend Code & Page Reference](#-frontend-code--page-reference)
6. [Interactive Simulation Modes](#-interactive-simulation-modes)
7. [Installation & Setup](#-installation--setup)
8. [Important Security Recommendations](#-important-security-recommendations)

---

## 🧠 Theoretical Concept & DTE Mechanics

### The Core Problem with Standard Encryption
Standard password managers use symmetric encryption (like AES-GCM or AES-CBC with PKCS#7 padding) to encrypt vault files. When an offline attacker attempts to brute-force a stolen vault file using tools like Hashcat:
1. They derive a key from a candidate password.
2. They decrypt the ciphertext.
3. They check for a **cryptographic failure signal** (e.g., invalid padding or a mismatched MAC tag).
4. If a padding/MAC error is encountered, they discard the key immediately (takes <1 microsecond). This allows attackers to try billions of passwords offline without detection.

### The Honey Encryption Solution
HoneyVault eliminates offline decryption failure signals.
* **No Padding/MAC Check:** It uses **AES-256-CTR (Counter Mode)**, which has no padding. Every key decrypts the ciphertext into *some* sequence of bytes without error.
* **Distribution Transforming Encoder (DTE):** The DTE decodes the decrypted byte array into plausible, human-readable credentials (website names, usernames, and passwords).
* **Decoys on Mismatch:**
  - Decrypting with the **correct master password** returns the user's authentic credentials.
  - Decrypting with **any incorrect master password** translates random decrypted noise into a set of 10 highly realistic-looking **decoy credentials**.
* **Blinded Attacker:** The attacker's offline cracking tool cannot automatically identify a wrong key. Every password tried yields a valid-looking credential database. To verify if a guess was correct, the attacker is forced to manually test the credentials online on actual web portals, which is slow, rate-limited, and highly detectable.

---

## 🌟 Core Features & Detailed How It Works Guide

### 1. DTE Honey Encryption (Deceptive Decryption)
* **Feature Description:** Decrypting the database with an incorrect master password does not return access denied or raw binary gibberish; it returns a functional list of fake credentials.
* **How It Works:**
  * When a decryption request arrives, the app retrieves the 504-byte file. Since the vault uses **AES-256-CTR**, the stream cipher runs without padding checks.
  * If the password is wrong, the derived key is incorrect. The decrypted block represents high-entropy pseudo-random garbage.
  * This garbage is passed to the DTE Decoder. Since DTE is designed to map any string of bits to a valid set of words from a predefined vocabulary, it maps the random bytes into structured website records.
  * To the attacker, the decryption succeeded completely, yielding readable usernames and passwords.

### 2. Distribution Transforming Encoder (DTE) Dictionary
* **Feature Description:** Natural language syllable tokenization that transforms raw binary outputs into readable, human-like words (e.g., `hadugo.com` or `xalego`) rather than random string garbage.
* **How It Works:**
  * The system uses a fixed vocabulary of **128 tokens** consisting of 72 alphanumeric characters and symbols, and 56 readable linguistic syllables (e.g., `ba`, `fi`, `ko`, `lu`, `ta`).
  * **Encoding:** Authentic user input strings are parsed using a greedy longest-match-first tokenizer. Each token corresponds to a 7-bit index (0-127). These indices are packed into fixed-width integers.
  * **Sanitization:** Decoying random byte streams could produce strange character sequences. If the system is in `Decoy` mode, three field-specific regex sanitizers scrub the fields:
    * *Site Sanitizer:* Strips arithmetic characters and ensures a valid TLD suffix (e.g., `.com`, `.net`, `.org`) is present.
    * *Username Sanitizer:* Ensures a valid name is followed by `@site` to simulate authentic company logins.
    * *Password Sanitizer:* Cleans up spaces and null characters but preserves security characters like `!` or `@` to maintain realism.

### 3. Deceptive Honey Canary Tracker Beacons
* **Feature Description:** Detection tracking embedded inside decoy credentials to trap and log unauthorized access.
* **How It Works:**
  * When the database is decrypted using an incorrect password, the DTE decoder generates 10 decoy records. 
  * The backend automatically modifies the first decoy entry (Index 0) and appends a hidden **canary beacon URL** in the form of `http://localhost:5000/canary?ref=<hash>&src=vault`.
  * If an attacker attempts to log in using the decoy credentials, their client or browser will request this URL.
  * The backend intercepts the HTTP query, records the attacker's external IP address, browser User-Agent, timestamp, and the exact wrong password they used, and then returns a 1x1 transparent tracker GIF. The attacker remains completely unaware they have been logged.

### 4. Interactive Binary Hex Dump & Byte Visualizer
* **Feature Description:** Interactive interface mapping the encrypted database structure on disk down to the byte level.
* **How It Works:**
  * When unlocked, the Vault dashboard allows users to inspect the raw database format.
  * The frontend makes a request to `/api/vault/raw`, which reads `honeyvault.enc` and converts the first 128 bytes to formatted hexadecimal strings.
  * The UI splits this raw data into an interactive color-coded banner detailing the exact block layout:
    * **Salt (16 bytes - Purple):** Used by PBKDF2 to derive the encryption key, preventing precomputed rainbow table attacks.
    * **IV/Nonce (8 bytes - Yellow):** PyCryptodome's initialization vector for AES-CTR mode.
    * **Ciphertext (480 bytes - Red):** The actual encrypted data containing the packed DTE bits.

### 5. Inactivity Auto-Lock Security Policy
* **Feature Description:** Automatic local and server-side session cleanup to protect left-behind screens.
* **How It Works:**
  * When a user successfully unlocks their vault, a countdown timer starts at 5 minutes (300 seconds).
  * A React hook (`useAutoLock.js`) sets event listeners on the `window` object for user interactions (`mousemove`, `keydown`, `click`, `scroll`). Any interaction resets the timer back to 300 seconds.
  * If the timer runs out, the hook triggers:
    1. A POST request to the backend `/api/vault/lock` endpoint to clear the secure cookie session.
    2. A frontend state reset inside `VaultContext.jsx` that clears the cached credential lists and redirects the browser to the login screen.

### 6. Interactive Online Brute-Force Terminal Simulator
* **Feature Description:** An animated Kali Linux terminal window simulation showing how Honey Encryption tricks online automated attacks.
* **How It Works:**
  * Users can type passwords or start an automated attack loop that tries common database passwords (like `password`, `admin123`, `dragon`).
  * The simulation makes actual HTTP calls to `/api/demo/attack` for each password.
  * Instead of returning `401 Unauthorized` or error screens, the server returns realistic-looking credentials and a success state, but logs a canary event in the background database. The attacker terminal receives valid-looking records for every single guess.

### 7. Side-by-Side Offline Attack Comparison Engine
* **Feature Description:** A comparative tool showing how standard encryption algorithms (AES-CBC) differ from DTE Honey Encryption under dictionary attacks.
* **How It Works:**
  * The app runs a wordlist against:
    * **Classic AES-CBC:** Shows how wrong passwords fail PKCS#7 padding validation, allowing the cracker to instantly discard them.
    * **Honey Encryption:** Shows how every single attempt successfully decrypts the file and returns a list of fake credentials.
  * **Step-by-Step Mode:** Steps through individual dictionary words, updating an interactive timeline. A reasoning panel explains what the cracking tool learns (e.g. *"Padding failed: discard key"* vs. *"Valid vault decoded: must verify online"*).

### 8. SQLite Central Security Console (Canary Logs & Audit Trails)
* **Feature Description:** An administrative panel showing login attempts, system state updates, and tracking beacon hits.
* **How It Works:**
  * The admin dashboard queries `/api/canary/hits`, `/api/audit/log`, and `/api/vault/meta`.
  * The page calculates statistics (Total login attempts, Canary tracker hits, and brute-force simulations) and shows them on metric cards.
  * A chronological data table displays details of threat attempts, helping developers study threat patterns.

---

## 🏛️ Architecture Overview

```
                        ┌────────────────────────────────────┐
                        │      React SPA Frontend (Vite)     │
                        └─────────────────┬──────────────────┘
                                          │ Axios HTTP Calls
                        ┌─────────────────▼──────────────────┐
                        │          Flask REST API            │
                        └──────┬──────────────────────┬──────┘
                               │                      │
       Local Filesystem Write  │                      │ Read / Write
┌──────────────────────────────▼──┐        ┌──────────▼─────────────────┐
│ honeyvault.enc (504B Encrypted) │        │ honeyvault.db (SQLite Logs)│
└─────────────────────────────────┘        └────────────────────────────┘
```

The repository is structured into two main components:
1. [backend/](file:///c:/code-2026/cns-el/cns-lab/backend/) — Flask API, encryption routines, and SQLite database logging.
2. [frontend/](file:///c:/code-2026/cns-el/cns-lab/frontend/) — React SPA providing the user dashboard, attack terminals, and log visualizers.

---

## ⚙️ Backend Code & Function Reference

The backend consists of four primary scripts that work together:

```
backend/
├── app.py                      # Flask routes and simulation APIs
├── honey_encryption.py          # Cryptographic key derivation and DTE logic
├── database.py                 # SQLite configuration and log insertions
└── vault.py                    # Filesystem read/write abstraction wrapper
```

---

### 1. [backend/app.py](file:///c:/code-2026/cns-el/cns-lab/backend/app.py)
This is the core Web server handling requests, cookie session storage, and attack simulations.

* **`create_vault()`** (Endpoint: `POST /api/vault/create`)
  * **Functionality:** Accepts a master password and starter entries. Validates password strength (length >= 8) and enforces a PoC limit of 10 credential slots. Checks if a vault already exists. Calls `save_vault()` to encrypt and write the file. Logs `VAULT_CREATED` to the audit log.
* **`vault_raw()`** (Endpoint: `GET /api/vault/raw`)
  * **Functionality:** Reads the encrypted `honeyvault.enc` binary directly from disk and converts the first 128 bytes to a readable hex dump. Returns metadata like file size and configuration parameters. Used to show the raw encrypted view in the frontend.
* **`unlock_vault()`** (Endpoint: `POST /api/vault/unlock`)
  * **Functionality:** Takes the user's master password guess. Invokes `load_vault()`, which returns decrypted entries and a boolean flag (`is_real`) indicating whether the password was correct. Sets session variables (`unlocked`, `is_real`, `entries`, `master_password`). 
  * **Security Policy:** If correct, logs `VAULT_UNLOCKED` and updates success counts. If incorrect, logs `FAILED_UNLOCK` to audit trails and logs a canary hit, storing the incorrect password. Both return `HTTP 200` to prevent timing/response leaks.
* **`get_entries()`** (Endpoint: `GET /api/vault/entries`)
  * **Functionality:** Returns the credential entries stored in the current session.
* **`add_entry()`** (Endpoint: `POST /api/vault/add`)
  * **Functionality:** Appends a new credential slot. If the session is a `Decoy` session, it silently returns success without modifying the file. If it is `Real`, it appends the new entry, calls `save_vault()` to re-encrypt and persist the updated vault, and returns the newly saved entry.
* **`lock_vault()`** (Endpoint: `POST /api/vault/lock`)
  * **Functionality:** Logs the user out by clearing the current Flask session memory.
* **`vault_status()`** (Endpoint: `GET /api/vault/status`)
  * **Functionality:** Returns whether the vault file exists on disk and if the user is logged in.
* **`demo_attack()`** (Endpoint: `POST /api/demo/attack`)
  * **Functionality:** Single-guess password tester for the online brute-force page. If the key is wrong, it registers a canary event before sending decoy credentials back.
* **`offline_attack_demo()`** (Endpoint: `POST /api/demo/offline-attack`)
  * **Functionality:** Performs a bulk simulated dictionary attack on two encryption strategies side-by-side: Classic AES-CBC and DTE Honey Encryption.
    1. **Phase 1 (Classic AES-CBC):** Simulates decryption. Wrong passwords instantly fail PKCS#7 padding validation, returning `INVALID_PADDING` (allowing the attacker to identify a wrong key offline).
    2. **Phase 2 (Honey Encryption):** Invokes DTE decryption for each word. All guesses return `DECOY` entries, preventing the attacker from discarding incorrect keys.
* **`offline_attack_guess()`** (Endpoint: `POST /api/demo/offline-attack/guess`)
  * **Functionality:** Evaluates a single guess for the interactive "Step-by-Step" offline simulator. Returns detailed side-by-side results and explanatory text for the attacker's reasoning panel.
* **`canary()`** (Endpoint: `GET /canary`)
  * **Functionality:** Returns a transparent 1x1 GIF tracking pixel. If loaded (e.g., when the attacker attempts to use a decoy credential containing this URL), it records a canary hit containing the client's IP address, User-Agent, and referenced seed.
* **`canary_hits()`** (Endpoint: `GET /api/canary/hits`)
  * **Functionality:** Retrieves recorded canary breaches from the database.
* **`audit_log()`** (Endpoint: `GET /api/audit/log`)
  * **Functionality:** Retrieves system audit records for the administrative dashboard.
* **`vault_meta()`** (Endpoint: `GET /api/vault/meta`)
  * **Functionality:** Exposes vault statistics (unlock and failure counts).

---

### 2. [backend/honey_encryption.py](file:///c:/code-2026/cns-el/cns-lab/backend/honey_encryption.py)
This is where the actual Honey Encryption and DTE Dictionaries are implemented.

* **DTE Vocabulary (`TOKENS`):** A fixed vocabulary of 128 elements (72 alphanumeric/special symbols + 56 syllables like `ba`, `fi`, `ta`, `lu`).
* **`tokenize_string(s)`**
  * **Functionality:** Greedily decomposes a string into vocabulary tokens. Matches the longest available syllables first (e.g., `github.com` splits to `gi`, `t`, `h`, `u`, `b`, `.`, `c`, `o`, `m`).
* **`tokens_to_bits(tokens, max_tokens)`**
  * **Functionality:** Converts a list of token strings into a single large integer representing a bitstring. Each token fits in 7 bits ($2^7 = 128$ tokens).
* **`bits_to_tokens(val, max_tokens)`**
  * **Functionality:** Performs the inverse of bit-packing, reading 7-bit blocks from a large integer and converting them back to string tokens.
* **Sanitization Routines (`_sanitize_site`, `_sanitize_username`, `_sanitize_password`):**
  * **Functionality:** When decrypting with a wrong key, the resulting random bytes yield arbitrary tokens containing spaces or invalid symbols. These functions clean up fields (e.g., stripping bad symbols, appending `.com` or `.org` to domain names, adding `@site` to usernames) so the generated decoy credentials look completely realistic.
* **`derive_key(password, salt)`**
  * **Functionality:** Executes PBKDF2-SHA256 over 200,000 iterations to derive a 256-bit symmetric AES key from the master password.
* **`encode_entry(entry, is_active)`**
  * **Functionality:** Packs an entry's website, username, password, and notes into exactly 47 bytes. Sets flag bits to optimize space if standard popular domains or usernames are used.
* **`decode_entry(data_bytes, index)`**
  * **Functionality:** Unpacks a 47-byte chunk into a credential dictionary using DTE decoding, applying field sanitizers if it decodes as a decoy.
* **`generate_mock_entry(i)`**
  * **Functionality:** Generates realistic filler credential structures to populate unused slots.
* **`encrypt_vault(entries, master_password)`**
  * **Functionality:** Encodes entries, adds a 4-byte magic signature (`HNYV`), pads up to 10 entries with mock data, generates a random salt and nonce, and encrypts using AES-CTR. Returns `[16-byte Salt] + [8-byte Nonce] + [480-byte Ciphertext]` (exactly 504 bytes on disk).
* **`decrypt_vault(data, master_password)`**
  * **Functionality:** Decrypts the 504-byte file. Verifies the `HNYV` magic header. 
    * If present: Returns the real user entries and sets `is_real=True`.
    * If absent (wrong password): Parses the resulting decrypted random noise through the DTE decoder, generates 10 plausible decoy credentials, embeds a custom tracking beacon in the first entry, and returns `is_real=False`.

---

### 3. [backend/database.py](file:///c:/code-2026/cns-el/cns-lab/backend/database.py)
Manages connection lifetimes and data storage inside the local SQLite file `honeyvault.db`.

* **`init_db()`**
  * **Functionality:** Prepares the SQLite database and creates three tables:
    1. `canary_hits`: Records timestamps, source IPs, User-Agents, incorrect passwords used, and trigger source references.
    2. `audit_log`: Stores timestamps, action names (e.g., `VAULT_CREATED`), detail notes, and IP addresses.
    3. `vault_meta`: Maintains vault creation details, unlock history counts, and failed password attempts.
* **`log_canary_hit(ip, user_agent, password_used, ref)` / `get_canary_hits()`**
  * **Functionality:** Writes or retrieves canary alert events.
* **`log_action(action, detail, ip)` / `get_audit_log()`**
  * **Functionality:** Writes or retrieves forensic audit records.
* **`create_vault_meta()` / `update_vault_meta(success)` / `get_vault_meta()`**
  * **Functionality:** Creates, modifies, or reads vault statistics.

---

### 4. [backend/vault.py](file:///c:/code-2026/cns-el/cns-lab/backend/vault.py)
Provides a clean interface for file operations on `honeyvault.enc`.

* **`vault_exists()`**
  * **Functionality:** Returns `True` if `honeyvault.enc` exists on the disk.
* **`save_vault(entries, master_password)`**
  * **Functionality:** Runs `encrypt_vault()` and writes the resulting 504-byte binary payload to disk.
* **`load_vault(master_password)`**
  * **Functionality:** Reads the 504-byte binary payload from disk and runs `decrypt_vault()`.

---

## 💻 Frontend Code & Page Reference

The frontend is a React application styled with clean, custom CSS.

```
frontend/src/
├── App.jsx                     # Layout routes and hooks wrapper
├── index.css                   # Global styling system
├── components/
│   └── Navbar.jsx              # Header navbar with session badges
├── context/
│   └── VaultContext.jsx        # Global React context for vault state
├── hooks/
│   └── useAutoLock.js          # Inactivity-based lock timer
├── pages/
│   ├── Setup.jsx               # Initial vault configuration page
│   ├── Unlock.jsx              # Vault unlocking interface
│   ├── Vault.jsx               # Main vault credentials display
│   ├── Demo.jsx                # Live online brute-force simulator
│   ├── OfflineAttack.jsx       # Interactive offline dictionary attack simulator
│   └── CanaryLog.jsx           # Canary incident and audit logs page
└── utils/
    └── passwordGenerator.js    # Utility to generate random passwords
```

---

### 1. [frontend/src/App.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/App.jsx)
Sets up the React Router layout. Wraps the routes in `VaultProvider` and invokes `useAutoLock` inside the `AppRoutes` container to apply the auto-lock security policy globally.

### 2. [frontend/src/context/VaultContext.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/context/VaultContext.jsx)
Maintains state across the application:
* `entries`: Active credentials (real or decoy).
* `isReal`: Security state indicator (`null` = locked, `true` = real vault, `false` = decoy vault).
* `unlocked`: Boolean indicating if the vault is currently unlocked.
* `lock()`: Function that clears all stored entries and resets security flags to lock the vault.

### 3. [frontend/src/hooks/useAutoLock.js](file:///c:/code-2026/cns-el/cns-lab/frontend/src/hooks/useAutoLock.js)
Tracks inactivity using browser events (`mousemove`, `keydown`, `click`, `scroll`). If no events occur for 5 minutes (300,000 ms), it automatically calls `/api/vault/lock` on the backend, runs the local `lock()` cleanup, and redirects the browser back to the login screen.

### 4. [frontend/src/pages/Setup.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Setup.jsx)
The setup interface. Appears when no `honeyvault.enc` file is found. Prompts the user to define a master password, displays the starter entries, and sends a creation request to `/api/vault/create`.

### 5. [frontend/src/pages/Unlock.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Unlock.jsx)
The login screen. Prompts the user for their master password. On submit, it posts to `/api/vault/unlock`, sets the credentials and security state in `VaultContext`, and redirects the user to the vault page.

### 6. [frontend/src/pages/Vault.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Vault.jsx)
The dashboard where users manage their credentials.
* **Badges:** Shows a green `✅ Real Vault` or red `🎭 Decoy Vault` badge.
* **Auto-Lock Timer:** Displays a real-time countdown timer synchronized with `useAutoLock`.
* **Add Entry:** Form to append new credentials.
* **Raw Hex Viewer (`RawVaultView`):** Fetches the raw file preview from `/api/vault/raw`. Renders a structural byte breakdown (showing the 16-byte Salt, 8-byte IV/Nonce, and 480-byte Ciphertext) along with an interactive hex dump.

### 7. [frontend/src/pages/Demo.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Demo.jsx)
Simulates an online brute-force attack.
* **Interactive Terminal:** Animates password attempts in a mock command-line interface.
* **Automatic Script:** Runs a list of common passwords sequentially. Displays how every single guess "succeeds" and returns plausible credentials, showing the attacker's confusion.

### 8. [frontend/src/pages/OfflineAttack.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/OfflineAttack.jsx)
An interactive playground simulating an offline dictionary attack against a stolen vault file.
* **Normal Mode:** Runs a wordlist against Classic AES-CBC and DTE Honey Encryption. Renders progress bars, stats (cracking speed, attempts, decoys generated), and comparative results.
* **Step-by-Step Mode:** Steps through one word at a time. Displays a side-by-side evaluation of both encryption schemes and provides a reasoning panel explaining what the attacker learns from each attempt.

### 9. [frontend/src/pages/CanaryLog.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/CanaryLog.jsx)
An administrative dashboard displaying the audit trail and logged canary hits. Displays the timestamp, source IP, trigger type, and the password used during the failed attempt.

---

## 🔄 Interactive Simulation Modes

### 1. Online Brute-Force Simulator (Demo Page)
Simulates an attacker trying to unlock the vault over the network:
* If the password is correct, they see the real credentials.
* If the password is wrong, Honey Encryption intercepts the request, logs the threat, and returns decoy data. The attacker sees no connection errors or validation failures.

### 2. Offline Attack Simulator (Offline Attack Page)
Demonstrates why Honey Encryption stops offline decryption tools:
* **Classic AES-CBC:** Decryption attempts fail instantly with padding errors. The cracking tool quickly finds the correct key.
* **DTE Honey Encryption:** Decryption attempts never fail. Every word tested produces a valid-looking database, forcing the attacker to verify entries online, which exposes them.

---

## 🚀 Installation & Setup

### Prerequisites
* Python 3.8 or higher
* Node.js v16 or higher

### 1. Backend Setup
Navigate to the backend directory, install the required packages, and start the Flask server:
```bash
cd cns-lab/backend
pip install -r requirements.txt
python app.py
```
This initializes the SQLite database (`honeyvault.db`) and starts the server on `http://127.0.0.1:5000`.

### 2. Frontend Setup
Navigate to the frontend directory, install dependencies, and start the development server:
```bash
cd cns-lab/frontend
npm install
npm run dev
```
Open your browser and navigate to `http://localhost:5173`.

---

## 🔒 Important Security Recommendations

This project is a Proof of Concept (PoC) designed to demonstrate the mechanics of Honey Encryption. For production deployments, note the following recommendations:

1. **Client-Side Decryption (Zero-Knowledge):** This PoC performs decryption on the Flask backend for demonstration purposes. In a production environment, all key derivation (PBKDF2) and decryption must happen on the client side (e.g., using the WebCrypto API) so the server never sees the master password or raw credentials.
2. **Remove the Magic Header:** The `HNYV` magic header is used in this PoC so the frontend can display the `Real` vs `Decoy` badge. In a real-world deployment, this header must be removed entirely. Its presence allows an attacker to verify the correct key offline.
3. **Entropy Calibration:** A production DTE must be calibrated against real-world password distributions using a comprehensive entropy model to prevent attackers from using statistical analysis to identify decoy vaults.
