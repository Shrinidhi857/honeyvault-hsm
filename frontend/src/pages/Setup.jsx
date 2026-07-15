import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useVault } from "../context/VaultContext";
import axios from "axios";

export default function Setup() {
    const [master, setMaster] = useState("");
    const [confirm, setConfirm] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const { setEntries, setIsReal, setUnlocked } = useVault();
    const navigate = useNavigate();

    // Starter entries pre-filled for demo
    const starterEntries = [
        { id: 1, site: "gmail.com", username: "john@gmail.com", password: "MyR3alP@ss!", notes: "Personal", created: "2024-01-01", canary: "" },
        { id: 2, site: "github.com", username: "john_dev", password: "G1tHub#Secret", notes: "Work", created: "2024-03-15", canary: "" },
        { id: 3, site: "amazon.in", username: "john@gmail.com", password: "Amaz0n$hop99", notes: "Shopping", created: "2024-06-10", canary: "" },
    ];

    async function handleSubmit(e) {
        e.preventDefault();
        setError("");
        if (master !== confirm) return setError("Passwords do not match.");
        if (master.length < 8) return setError("Master password must be at least 8 characters.");
        setLoading(true);
        try {
            const res = await axios.post("/api/vault/create", {
                master_password: master,
                entries: starterEntries
            }, { withCredentials: true });

            setEntries(starterEntries);
            setIsReal(true);
            setUnlocked(true);
            navigate("/vault");
        } catch (err) {
            setError(err.response?.data?.error || "Failed to create vault.");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div style={{ minHeight: "calc(100vh - 60px)", display: "flex", alignItems: "center", justifyContent: "center", padding: "2rem" }}>
            <div style={{ width: "100%", maxWidth: 440 }}>

                {/* Header */}
                <div className="text-center mb-4">
                    <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🍯</div>
                    <h2 style={{ fontWeight: 700, marginBottom: 6 }}>Create Your Vault</h2>
                    <p className="text-muted" style={{ fontSize: "0.88rem", lineHeight: 1.6 }}>
                        Choose a strong master password. Every wrong attempt will return a realistic fake vault — the attacker will never know they failed.
                    </p>
                </div>

                <div className="card">
                    {error && <div className="alert alert-red">{error}</div>}

                    <form onSubmit={handleSubmit}>
                        <div className="form-group">
                            <label className="form-label">Master Password</label>
                            <input className="form-input mono" type="password" placeholder="Min. 8 characters"
                                value={master} onChange={e => setMaster(e.target.value)} required />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Confirm Password</label>
                            <input className="form-input mono" type="password" placeholder="Re-enter master password"
                                value={confirm} onChange={e => setConfirm(e.target.value)} required />
                        </div>

                        <hr className="divider" />

                        <div style={{ marginBottom: "1rem" }}>
                            <p style={{ fontSize: "0.78rem", color: "var(--muted)", marginBottom: "0.5rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                                Starter entries (pre-loaded for demo)
                            </p>
                            {starterEntries.map(e => (
                                <div key={e.id} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: "0.83rem" }}>
                                    <span style={{ color: "var(--purple)" }}>{e.site}</span>
                                    <span className="text-muted mono">{e.username}</span>
                                </div>
                            ))}
                        </div>

                        <button type="submit" className="btn btn-purple btn-full" disabled={loading}>
                            {loading ? "Creating vault..." : "🔐 Create Vault"}
                        </button>
                    </form>
                </div>

                <p className="text-center mt-2" style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
                    Already have a vault? <a href="/unlock" style={{ color: "var(--purple)" }}>Unlock it</a>
                </p>
            </div>
        </div>
    );
}