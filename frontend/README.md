# 🍯 HoneyVault: React + Vite Frontend

This directory contains the single-page application (SPA) frontend for the **HoneyVault Honey Encryption Password Manager PoC**. 

For a complete explanation of the cryptographic backend, SQLite database schema, and detailed functions, please refer to the main [cns-lab/README.md](file:///c:/code-2026/cns-el/cns-lab/README.md).

---

## 🛠️ Technology Stack
* **Framework:** React 19 (using JSX and modern functional hooks)
* **Build Tool:** Vite 8 (utilizing Rolldown under the hood)
* **Styling:** Vanilla CSS with custom layout definitions (configured via [index.css](file:///c:/code-2026/cns-el/cns-lab/frontend/src/index.css))
* **Routing:** React Router DOM (v7)
* **HTTP Client:** Axios (configured with credentials support for session cookies)

---

## 📂 Directory Structure

```
frontend/
├── package.json
├── vite.config.js              # Vite server proxies and plugin configurations
├── public/                     # Static assets
└── src/
    ├── App.jsx                 # Routing layout and global hooks wrapper
    ├── index.css               # Core CSS design system
    ├── components/
    │   └── Navbar.jsx          # Header with session badges (Real/Decoy)
    ├── context/
    │   └── VaultContext.jsx    # React Context for global logged-in session state
    ├── hooks/
    │   └── useAutoLock.js      # Global inactivity tracker and auto-locker hook
    ├── pages/
    │   ├── Setup.jsx           # Vault initialization form
    │   ├── Unlock.jsx          # Master password entry page
    │   ├── Vault.jsx           # Main entries table, countdown timer, and Hex Viewer
    │   ├── Demo.jsx            # Interactive online brute-force terminal simulation
    │   ├── OfflineAttack.jsx   # Side-by-side AES-CBC vs DTE attack simulator
    │   └── CanaryLog.jsx       # Threat monitoring and admin audit logs
    └── utils/
        └── passwordGenerator.js# Secure random password generator and strength evaluator
```

---

## 🚦 Application Routes & Views

The frontend maps path routes to specific pages using [frontend/src/App.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/App.jsx):

* **`/setup`** ([Setup.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Setup.jsx)): 
  * Appears if no vault has been created. Preloaded with starter credentials, it allows the user to initialize a vault with a master password.
* **`/unlock`** ([Unlock.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Unlock.jsx)): 
  * Prompts the user to enter their master password. Passes key credentials to the backend.
* **`/vault`** ([Vault.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Vault.jsx)): 
  * The central user dashboard. Displays a table of credentials. Displays either a green `✅ Real Vault` or a red `🎭 Decoy Vault` badge depending on the password correctness. Includes an interactive **Raw Hex Viewer** component showcasing the structure of the encrypted file (`honeyvault.enc`).
* **`/demo`** ([Demo.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/Demo.jsx)): 
  * Simulates an online brute-force scenario inside an animated terminal, logging canary events when incorrect keys are tested.
* **`/offline-attack`** ([OfflineAttack.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/OfflineAttack.jsx)): 
  * Runs dictionary files offline to compare standard AES (which crashes on padding errors) and Honey Encryption (which decrypts silently to fake entries). Offers both a bulk runner and a step-by-step visualizer with a developer explanation panel.
* **`/canary`** ([CanaryLog.jsx](file:///c:/code-2026/cns-el/cns-lab/frontend/src/pages/CanaryLog.jsx)): 
  * Renders logs of all threat events (canary alerts, failed login passwords, brute-force logs).

---

## 🌟 Core Frontend Features & How They Work

### 1. Inactivity-Based Auto-Lock Hook (`useAutoLock.js`)
* **Feature:** Automatically secures the active user session when the application is left unattended.
* **How It Works:**
  * Uses the browser event loop to listen for user activity events: `mousemove`, `keydown`, `click`, and `scroll`.
  * Maintains a JavaScript timeout pointer `timer.current`.
  * If any event is captured, `timer.current` is cleared and reset to trigger in 5 minutes (300,000 milliseconds).
  * If the timer fires, the hook triggers a POST call to `/api/vault/lock` to tell the Flask server to clear session keys. It then executes the context's clean-up callback and pushes the router destination to `/unlock`.

### 2. State synchronization (`VaultContext.jsx`)
* **Feature:** High-availability session persistence that ensures component visibility checks match security policies.
* **How It Works:**
  * Uses a global React context wrapper (`VaultProvider`) wrapped around the root route router.
  * Exports states (`unlocked`, `isReal`, `entries`) to check authentication throughout child pages.
  * Exposes a `lock()` action that instantly clears the state memory array (`entries`), resets validation flags (`isReal` to `null`), and sets `unlocked` to `false` to block unauthorized screen caching.

### 3. Raw Encrypted Binary Hex Viewer (`Vault.jsx`)
* **Feature:** Visual representation of the encrypted on-disk file formatting.
* **How It Works:**
  * The `/vault` route renders a hidden container `<RawVaultView />` that queries `/api/vault/raw` on activation.
  * It translates the returned byte size into a structure showing the first 16 bytes (Salt block), the next 8 bytes (IV block), and the remainder (AES-CTR Ciphertext).
  * It displays the returned hexadecimal dump in a pre-formatted box with monospaced styling (`JetBrains Mono`).

### 4. Attack Animation Terminals (`Demo.jsx` & `OfflineAttack.jsx`)
* **Feature:** Simulated threat CLI logs animating bulk dictionary operations.
* **How It Works:**
  * Uses timer loops to run through array guesses.
  * In the **Online Simulator (`Demo.jsx`)**, it updates terminal logs line-by-line using standard arrays.
  * In the **Offline Simulator (`OfflineAttack.jsx`)**, it displays side-by-side cards evaluating each password guess, calculating timing logs, and rendering reasoning summaries describing why padding signals let crackers bypass standard schemes while Honey Encryption holds.

---

## 🏃 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Run the Development Server
```bash
npm run dev
```
By default, the server runs at `http://localhost:5173`. Ensure the Flask backend is running on port `5000` to handle API queries.
