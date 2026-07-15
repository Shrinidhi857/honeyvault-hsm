import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useVault } from "../context/VaultContext";
import { generatePassword, getStrength } from "../utils/passwordGenerator";
import axios from "axios";

const TIMEOUT_SEC = 5 * 60; // must match TIMEOUT_MS in useAutoLock (5 min = 300 sec)
function RawVaultView() {
  const [raw, setRaw] = useState(null);

  useEffect(() => {
    axios.get("/api/vault/raw", { withCredentials: true })
      .then(r => setRaw(r.data))
      .catch(() => setRaw(null));
  }, []);

  if (!raw) return <p className="text-muted" style={{ fontSize:"0.82rem" }}>Loading...</p>;

  return (
    <div>
      {/* Metadata */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:"1rem", marginBottom:"1rem" }}>
        {[
          ["Algorithm",  "AES-256-CBC"],
          ["Key derivation", "PBKDF2-SHA256 · 200k iterations"],
          ["File size",  `${raw.size_bytes} bytes`],
        ].map(([label, val]) => (
          <div key={label} style={{ background:"var(--bg)", borderRadius:8, padding:"0.8rem 1rem" }}>
            <p style={{ fontSize:"0.72rem", color:"var(--muted)", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.04em", margin:0 }}>{label}</p>
            <p style={{ fontSize:"0.85rem", fontWeight:600, margin:"4px 0 0", fontFamily:"'JetBrains Mono',monospace", color:"var(--purple)" }}>{val}</p>
          </div>
        ))}
      </div>

      {/* Structure breakdown */}
      <div style={{ display:"flex", gap:4, marginBottom:"1rem", fontFamily:"'JetBrains Mono',monospace", fontSize:"0.75rem" }}>
        {[
          { label:"SALT",       bytes:"16 bytes",  color:"rgba(124,111,247,0.3)", text:"var(--purple)" },
          { label:"IV",         bytes:"16 bytes",  color:"rgba(234,179,8,0.3)",   text:"var(--yellow)" },
          { label:"CIPHERTEXT", bytes:`${raw.size_bytes - 32} bytes`, color:"rgba(239,68,68,0.3)", text:"var(--red)" },
        ].map(({ label, bytes, color, text }) => (
          <div key={label} style={{ background:color, borderRadius:6, padding:"6px 12px", flex: label==="CIPHERTEXT" ? 3 : 1 }}>
            <div style={{ color:text, fontWeight:700 }}>{label}</div>
            <div style={{ color:"var(--muted)" }}>{bytes}</div>
          </div>
        ))}
      </div>

      {/* Hex dump */}
      <div style={{ background:"#0a0a0f", borderRadius:8, padding:"1rem", overflowX:"auto" }}>
        <p style={{ fontSize:"0.7rem", color:"var(--muted)", marginBottom:"0.5rem", fontWeight:600 }}>
          HEX DUMP — first 128 bytes of vault.enc
        </p>
        <pre style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:"0.75rem", color:"#4ade80", margin:0, lineHeight:1.8, whiteSpace:"pre-wrap", wordBreak:"break-all" }}>
          {raw.hex_preview}
        </pre>
        <p style={{ fontSize:"0.72rem", color:"var(--muted)", marginTop:"0.5rem", margin:"0.5rem 0 0" }}>
          ← Your passwords are hidden inside this binary data. Without the master password, this is unreadable.
        </p>
      </div>
    </div>
  );
}
export default function Vault() {
    const { entries, setEntries, isReal, unlocked } = useVault();
    const [showAdd, setShowAdd] = useState(false);
    const [revealed, setRevealed] = useState({});
    const [search, setSearch] = useState("");
    const [msg, setMsg] = useState("");
    const [loading, setLoading] = useState(false);
    const [countdown, setCountdown] = useState(TIMEOUT_SEC);
    const [form, setForm] = useState({ site: "", username: "", password: "", notes: "" });
    const navigate = useNavigate();
    const [showRaw,   setShowRaw]   = useState(false);  // ← add this
    // Fetch entries on mount
    useEffect(() => {
        if (!unlocked) { navigate("/unlock"); return; }
        axios.get("/api/vault/entries", { withCredentials: true })
            .then(r => setEntries(r.data.entries))
            .catch(() => navigate("/unlock"));
    }, []);

    // Countdown display — mirrors useAutoLock timer, resets on activity
    useEffect(() => {
        if (!unlocked) return;
        setCountdown(TIMEOUT_SEC);
        const tick = setInterval(() => setCountdown(c => Math.max(0, c - 1)), 1000);
        const reset = () => setCountdown(TIMEOUT_SEC);
        const events = ["mousemove", "keydown", "click", "scroll"];
        events.forEach(e => window.addEventListener(e, reset));
        return () => {
            clearInterval(tick);
            events.forEach(e => window.removeEventListener(e, reset));
        };
    }, [unlocked]);

    function formatCountdown(sec) {
        const m = Math.floor(sec / 60).toString().padStart(2, "0");
        const s = (sec % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    }

    function toggleReveal(id) {
        setRevealed(prev => ({ ...prev, [id]: !prev[id] }));
    }

    async function handleAdd(e) {
        e.preventDefault();
        setLoading(true);
        try {
            await axios.post("/api/vault/add", form, { withCredentials: true });
            const newEntry = {
                ...form,
                id: entries.length + 1,
                created: new Date().toISOString().slice(0, 10),
                canary: ""
            };
            setEntries([...entries, newEntry]);
            setForm({ site: "", username: "", password: "", notes: "" });
            setShowAdd(false);
            setMsg("✅ Entry saved successfully.");
            setTimeout(() => setMsg(""), 3000);
        } catch {
            setMsg("❌ Failed to save entry.");
        } finally {
            setLoading(false);
        }
    }

    // Filter entries by search query
    const filtered = entries.filter(e =>
        e.site.toLowerCase().includes(search.toLowerCase()) ||
        e.username.toLowerCase().includes(search.toLowerCase())
    );

    const strength = form.password ? getStrength(form.password) : null;

    return (
        <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem" }}>

            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                <div>
                    <h2 style={{ fontWeight: 700, marginBottom: 4 }}>🍯 Your Vault</h2>
                    <p className="text-muted" style={{ fontSize: "0.85rem" }}>
                        {entries.length} entries · {filtered.length} shown
                    </p>
                </div>
                <div style={{ display: "flex", gap: "0.8rem", alignItems: "center" }}>

                    {/* Auto-lock countdown */}
                    <div style={{
                        background: countdown < 60 ? "rgba(239,68,68,0.1)" : "rgba(255,255,255,0.04)",
                        border: `1px solid ${countdown < 60 ? "rgba(239,68,68,0.3)" : "var(--border)"}`,
                        borderRadius: 8, padding: "5px 12px", fontSize: "0.78rem",
                        fontFamily: "'JetBrains Mono', monospace",
                        color: countdown < 60 ? "var(--red)" : "var(--muted)",
                        transition: "all 0.3s"
                    }}>
                        🔒 {formatCountdown(countdown)}
                    </div>

                    {isReal === true && <span className="badge badge-green">✅ Real Vault</span>}
                    {isReal === false && <span className="badge badge-red">🎭 Decoy Vault</span>}
                    <button className="btn btn-purple btn-sm" onClick={() => setShowAdd(!showAdd)}>
                        + Add Entry
                    </button>
                </div>
            </div>

            {/* Decoy warning */}
            {isReal === false && (
                <div className="alert alert-yellow" style={{ marginBottom: "1rem" }}>
                    <strong>🎭 Honey Encryption Active:</strong> Wrong password was used.
                    This is a decoy vault — all entries below are fake. The real vault is untouched.
                </div>
            )}

            {msg && (
                <div className={`alert ${msg.startsWith("✅") ? "alert-green" : "alert-red"}`} style={{ marginBottom: "1rem" }}>
                    {msg}
                </div>
            )}

            {/* Search bar */}
            <div style={{ marginBottom: "1rem", position: "relative" }}>
                <span style={{
                    position: "absolute", left: 12, top: "50%",
                    transform: "translateY(-50%)", color: "var(--muted)", fontSize: "0.9rem",
                    pointerEvents: "none"
                }}>🔍</span>
                <input
                    className="form-input"
                    placeholder="Search by site or username..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    style={{ paddingLeft: 36 }}
                />
            </div>

            {/* Add entry form */}
            {showAdd && (
                <div className="card" style={{ marginBottom: "1.5rem" }}>
                    <h6 style={{ fontWeight: 600, marginBottom: "1rem" }}>New Entry</h6>
                    <form onSubmit={handleAdd}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>

                            <div className="form-group">
                                <label className="form-label">Site</label>
                                <input className="form-input" placeholder="e.g. gmail.com"
                                    value={form.site}
                                    onChange={e => setForm({ ...form, site: e.target.value })}
                                    required />
                            </div>

                            <div className="form-group">
                                <label className="form-label">Username / Email</label>
                                <input className="form-input" placeholder="e.g. john@gmail.com"
                                    value={form.username}
                                    onChange={e => setForm({ ...form, username: e.target.value })}
                                    required />
                            </div>

                            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                                <label className="form-label">Password</label>
                                <div style={{ display: "flex", gap: 6 }}>
                                    <input className="form-input mono"
                                        placeholder="Enter or generate a password"
                                        value={form.password}
                                        onChange={e => setForm({ ...form, password: e.target.value })}
                                        required style={{ flex: 1 }} />
                                    <button type="button" className="btn btn-ghost btn-sm"
                                        onClick={() => setForm({ ...form, password: generatePassword() })}>
                                        🎲 Generate
                                    </button>
                                </div>

                                {/* Strength meter */}
                                {strength && (
                                    <div style={{ marginTop: 8 }}>
                                        <div style={{ height: 4, background: "var(--border)", borderRadius: 99, overflow: "hidden" }}>
                                            <div style={{
                                                height: "100%", width: strength.width,
                                                background: strength.color, borderRadius: 99,
                                                transition: "width 0.3s, background 0.3s"
                                            }} />
                                        </div>
                                        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                                            <span style={{ fontSize: "0.75rem", color: strength.color, fontWeight: 600 }}>
                                                {strength.label}
                                            </span>
                                            <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
                                                {form.password.length} chars
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                                <label className="form-label">Notes (optional)</label>
                                <input className="form-input" placeholder="e.g. Personal account"
                                    value={form.notes}
                                    onChange={e => setForm({ ...form, notes: e.target.value })} />
                            </div>
                        </div>

                        <div style={{ display: "flex", gap: "0.8rem", marginTop: "0.5rem" }}>
                            <button type="submit" className="btn btn-purple" disabled={loading}>
                                {loading ? "Saving..." : "Save Entry"}
                            </button>
                            <button type="button" className="btn btn-ghost"
                                onClick={() => { setShowAdd(false); setForm({ site: "", username: "", password: "", notes: "" }); }}>
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* Entries table or empty state */}
            {filtered.length === 0 ? (
                <div className="card text-center" style={{ padding: "3rem" }}>
                    <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>
                        {search ? "🔍" : "🍯"}
                    </div>
                    <p style={{ fontWeight: 600, marginBottom: 6 }}>
                        {search ? `No entries matching "${search}"` : "No entries yet"}
                    </p>
                    <p className="text-muted" style={{ fontSize: "0.85rem" }}>
                        {search ? "Try a different search term." : "Click + Add Entry to get started."}
                    </p>
                </div>
            ) : (
                <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                        <thead>
                            <tr style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid var(--border)" }}>
                                {["Site", "Username", "Password", "Notes", "Added", ""].map(h => (
                                    <th key={h} style={{
                                        padding: "12px 16px", textAlign: "left",
                                        fontSize: "0.72rem", fontWeight: 700,
                                        textTransform: "uppercase", letterSpacing: "0.06em",
                                        color: "var(--muted)"
                                    }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {filtered.map((e, i) => (
                                <tr key={e.id}
                                    style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none" }}
                                    onMouseOver={ev => ev.currentTarget.style.background = "var(--bg-hover)"}
                                    onMouseOut={ev => ev.currentTarget.style.background = ""}>
                                    <td style={{ padding: "12px 16px" }}>
                                        <span style={{ color: "var(--purple)", fontWeight: 600 }}>{e.site}</span>
                                    </td>
                                    <td style={{ padding: "12px 16px", color: "var(--muted)" }}>{e.username}</td>
                                    <td style={{ padding: "12px 16px" }}>
                                        <span className="mono" style={{
                                            color: revealed[e.id] ? "var(--green)" : "var(--muted)",
                                            letterSpacing: revealed[e.id] ? "normal" : "0.15em"
                                        }}>
                                            {revealed[e.id] ? e.password : "••••••••••"}
                                        </span>
                                    </td>
                                    <td style={{ padding: "12px 16px", color: "var(--muted)", fontSize: "0.8rem" }}>
                                        {e.notes || "—"}
                                    </td>
                                    <td style={{ padding: "12px 16px", color: "var(--muted)", fontSize: "0.78rem" }}>
                                        {e.created}
                                    </td>
                                    <td style={{ padding: "12px 16px" }}>
                                        <button className="btn btn-ghost btn-sm" onClick={() => toggleReveal(e.id)}>
                                            {revealed[e.id] ? "Hide" : "Show"}
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
            {/* Raw encrypted vault viewer */}
<div className="card" style={{ marginTop:"1.5rem" }}>
  <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.8rem" }}>
    <div>
      <p style={{ fontWeight:600, margin:0 }}>🔐 Raw Encrypted Vault</p>
      <p className="text-muted" style={{ fontSize:"0.78rem", margin:0 }}>
        This is what an attacker sees when they steal the vault file
      </p>
    </div>
    <button className="btn btn-ghost btn-sm" onClick={() => setShowRaw(!showRaw)}>
      {showRaw ? "Hide" : "Show Raw"}
    </button>
  </div>

  {showRaw && (
    <RawVaultView />
  )}
</div>
        </div>
    );
}