import { Link, useNavigate } from "react-router-dom";
import { useVault } from "../context/VaultContext";
import axios from "axios";

export default function Navbar() {
    const { unlocked, isReal, lock } = useVault();
    const navigate = useNavigate();

    async function handleLock() {
        await axios.post("/api/vault/lock", {}, { withCredentials: true });
        lock();
        navigate("/unlock");
    }

    return (
        <nav style={{
            background: "#13131a",
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            padding: "0 2rem", height: 60,
            display: "flex", alignItems: "center", justifyContent: "space-between",
            position: "sticky", top: 0, zIndex: 100
        }}>
            {/* Logo */}
            <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                    width: 32, height: 32, background: "var(--purple)",
                    borderRadius: 8, display: "flex", alignItems: "center",
                    justifyContent: "center", fontSize: "1rem"
                }}>🍯</div>
                <span style={{ fontWeight: 700, fontSize: "1rem", color: "var(--text)" }}>
                    Honey<span style={{ color: "var(--purple)" }}>Vault</span>
                </span>
            </Link>

            {/* Links */}
            <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
                {unlocked && (
                    <>
                        <Link to="/vault" style={{ color: "var(--muted)", textDecoration: "none", fontSize: "0.88rem", fontWeight: 500 }}>
                            🔐 Vault
                        </Link>
                    </>
                )}

                {/* Session status badge */}
                {unlocked && isReal === true && <span className="badge badge-green">● Real Session</span>}
                {unlocked && isReal === false && <span className="badge badge-red">● Decoy Session</span>}

                {unlocked && (
                    <button className="btn btn-ghost btn-sm" onClick={handleLock}>
                        Lock Vault
                    </button>
                )}
            </div>
        </nav>
    );
}