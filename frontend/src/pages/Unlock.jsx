import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useVault } from "../context/VaultContext";
import axios from "axios";

// Hardware status hook
function useHardwareStatus() {
    const [hw, setHw] = useState(null);
    useEffect(() => {
        axios.get("/api/hardware/status", { withCredentials: true })
            .then(r => setHw(r.data))
            .catch(() => setHw({ gpio_available: false, mode: "SIMULATED", timeout_seconds: 10 }));
    }, []);
    return hw;
}

export default function Unlock() {
    const [master, setMaster]             = useState("");
    const [error, setError]               = useState("");
    const [loading, setLoading]           = useState(false);
    const [hasVault, setHasVault]         = useState(null);
    const [awaitingGate, setAwaitingGate] = useState(false);
    const [countdown, setCountdown]       = useState(10);
    const [simPressed, setSimPressed]     = useState(false);
    const [showPass, setShowPass]         = useState(false);

    const { setEntries, setIsReal, setUnlocked } = useVault();
    const navigate = useNavigate();
    const hw       = useHardwareStatus();
    const timerRef = useRef(null);

    useEffect(() => {
        axios.get("/api/vault/status", { withCredentials: true })
            .then(r => setHasVault(r.data.vault_exists))
            .catch(() => setHasVault(false));
    }, []);

    useEffect(() => {
        if (awaitingGate) {
            const total = hw?.timeout_seconds ?? 10;
            setCountdown(total);
            timerRef.current = setInterval(() => {
                setCountdown(prev => Math.max(0, prev - 1));
            }, 1000);
        } else {
            clearInterval(timerRef.current);
        }
        return () => clearInterval(timerRef.current);
    }, [awaitingGate, hw]);

    async function handleSimulate() {
        if (simPressed) return;
        setSimPressed(true);
        try { await axios.post("/api/demo/press-button", {}, { withCredentials: true }); }
        catch (_) {}
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError("");
        setAwaitingGate(true);
        setSimPressed(false);

        try {
            const res = await axios.post(
                "/api/vault/unlock",
                { master_password: master },
                { withCredentials: true, timeout: ((hw?.timeout_seconds ?? 10) + 4) * 1000 }
            );
            setEntries(res.data.entries);
            setIsReal(res.data.is_real);
            setUnlocked(true);
            navigate("/vault");
        } catch (err) {
            const data   = err.response?.data;
            const isGate = data?.gate_timeout;
            setError(
                isGate
                    ? "Hardware confirmation timed out. No button press was detected within 10 seconds."
                    : data?.error || "Failed to unlock vault. Please try again."
            );
        } finally {
            setLoading(false);
            setAwaitingGate(false);
        }
    }

    if (hasVault === null) return (
        <div className="unlock-page">
            <div className="unlock-center">
                <div className="spinner" />
                <p className="text-muted" style={{ marginTop: "1rem", textAlign: "center" }}>Checking vault status...</p>
            </div>
        </div>
    );

    const total = hw?.timeout_seconds ?? 10;
    const circumference = 2 * Math.PI * 34;

    return (
        <div className="unlock-page">
            <div className="unlock-center">

                {/* Header */}
                <div className="unlock-header">
                    <div className="lock-icon-wrap">
                        <span className="lock-icon">{awaitingGate ? "🔄" : "🔐"}</span>
                    </div>
                    <h1 className="unlock-title">
                        {awaitingGate ? "Awaiting Physical Confirmation" : "Unlock Vault"}
                    </h1>
                    <p className="unlock-subtitle">
                        {awaitingGate
                            ? "Press the tactile button wired to GPIO 17 on your Raspberry Pi to authorize vault access."
                            : hasVault
                                ? "Enter your master password. A physical button press on the Pi is required to release the vault."
                                : "No vault found. Create one to get started."}
                    </p>
                </div>

                {/* Physical Gate Overlay */}
                {awaitingGate && (
                    <div className="gate-overlay">
                        <div className="gate-pulse-wrapper">
                            <div className="gate-ring ring-1" />
                            <div className="gate-ring ring-2" />
                            <div className="gate-ring ring-3" />
                            <div className="gate-btn-icon">🔘</div>
                        </div>

                        <div className="gate-countdown">
                            <svg viewBox="0 0 80 80" className="countdown-svg">
                                <circle cx="40" cy="40" r="34" className="countdown-track" />
                                <circle
                                    cx="40" cy="40" r="34"
                                    className="countdown-fill"
                                    style={{
                                        strokeDasharray: circumference,
                                        strokeDashoffset: circumference * (1 - countdown / total),
                                    }}
                                />
                            </svg>
                            <div className="countdown-number">{countdown}</div>
                        </div>

                        <p className="gate-label">seconds remaining</p>

                        <div className={`gate-mode-badge ${hw?.gpio_available ? "badge-green" : "badge-yellow"}`}>
                            {hw?.gpio_available ? "🟢 Real GPIO — Raspberry Pi" : "🟡 Simulated — PC Dev Mode"}
                        </div>

                        {!hw?.gpio_available && (
                            <button
                                id="simulate-btn"
                                className={`btn btn-purple btn-simulate ${simPressed ? "btn-pressed" : ""}`}
                                onClick={handleSimulate}
                                disabled={simPressed}
                            >
                                {simPressed ? "✅ Button Press Sent" : "🖱 Simulate Button Press (PC Testing)"}
                            </button>
                        )}

                        <p className="gate-wire-hint">
                            Wiring: <code>GPIO 17</code> → Tactile Button → <code>GND</code>
                        </p>
                    </div>
                )}

                {/* Login Card */}
                {!awaitingGate && hasVault && (
                    <div className="card">
                        {error && <div className="alert alert-red">{error}</div>}

                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label className="form-label" htmlFor="master-password-input">Master Password</label>
                                <div style={{ position: "relative" }}>
                                    <input
                                        id="master-password-input"
                                        className="form-input mono"
                                        type={showPass ? "text" : "password"}
                                        placeholder="Enter master password..."
                                        autoFocus
                                        value={master}
                                        onChange={e => setMaster(e.target.value)}
                                        required
                                        style={{ paddingRight: "2.5rem" }}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPass(p => !p)}
                                        style={{
                                            position: "absolute", right: 10, top: "50%",
                                            transform: "translateY(-50%)",
                                            background: "none", border: "none",
                                            cursor: "pointer", color: "var(--muted)", fontSize: "0.85rem"
                                        }}
                                        aria-label="Toggle password visibility"
                                    >
                                        {showPass ? "🙈" : "👁"}
                                    </button>
                                </div>
                            </div>
                            <button
                                id="unlock-btn"
                                type="submit"
                                className="btn btn-purple btn-full"
                                disabled={loading || !master}
                            >
                                {loading ? "Waiting for hardware confirmation..." : "Unlock Vault →"}
                            </button>
                        </form>

                        <hr className="divider" />

                        <div className="gate-info-panel">
                            <div className="gate-info-row">
                                <span className="gate-info-icon">🛡</span>
                                <div>
                                    <p className="gate-info-title">Physical Presence Gate</p>
                                    <p className="gate-info-desc">
                                        After entering your password you have <strong>10 seconds</strong> to press
                                        the button on your Pi. Even with your password, a remote attacker cannot
                                        trigger the release — they cannot press a button on your desk.
                                    </p>
                                </div>
                            </div>
                            <div className="gate-info-row">
                                <span className="gate-info-icon">🍯</span>
                                <div>
                                    <p className="gate-info-title">Honey Encryption Active</p>
                                    <p className="gate-info-desc">
                                        Every wrong password decrypts to a realistic fake vault. Attackers never
                                        see "Access Denied."
                                    </p>
                                </div>
                            </div>
                            <div className="gate-info-row">
                                <span className="gate-info-icon">🐦</span>
                                <div>
                                    <p className="gate-info-title">Canary Tracker</p>
                                    <p className="gate-info-desc">
                                        Decoy credentials contain hidden tracking beacons. If an attacker tests
                                        stolen fake credentials, you get an alert with their IP.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <p className="text-center mt-2" style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                            Demo password: <code style={{ color: "var(--purple)" }}>MasterPassword123!</code>
                        </p>
                    </div>
                )}

                {/* No vault state */}
                {!awaitingGate && !hasVault && (
                    <div className="card text-center">
                        <p className="text-muted" style={{ marginBottom: "1.2rem" }}>
                            No encrypted vault exists on this device yet.
                        </p>
                        <a href="/setup" id="create-vault-btn" className="btn btn-purple">
                            + Create New Vault
                        </a>
                    </div>
                )}

            </div>
        </div>
    );
}
