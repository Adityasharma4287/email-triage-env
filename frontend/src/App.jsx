import { useState, useEffect, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";

const PRIORITY_CONFIG = {
  urgent: { color: "#FF3B30", bg: "#FF3B3012", label: "URGENT", icon: "⚡" },
  high:   { color: "#FF9500", bg: "#FF950012", label: "HIGH",   icon: "🔺" },
  medium: { color: "#34C759", bg: "#34C75912", label: "MEDIUM", icon: "◆" },
  low:    { color: "#636366", bg: "#63636612", label: "LOW",    icon: "▼" },
  spam:   { color: "#FF453A", bg: "#FF453A12", label: "SPAM",   icon: "🚫" },
};

const CATEGORY_ICONS = {
  customer_support: "👤",
  billing: "💳",
  technical: "⚙️",
  sales: "📈",
  internal: "🏢",
  spam: "⛔",
  other: "📌",
};

// ─── Animated counter ────────────────────────────────────────────────────────
function AnimatedNumber({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    const start = display;
    const end = value;
    const duration = 600;
    const startTime = performance.now();

    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + (end - start) * eased;
      setDisplay(decimals > 0 ? parseFloat(current.toFixed(decimals)) : Math.round(current));
      if (progress < 1) ref.current = requestAnimationFrame(animate);
    };

    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [value]);

  return <span>{decimals > 0 ? display.toFixed(decimals) : display}</span>;
}

// ─── Score ring ───────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 120 }) {
  const r = 46;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - score);
  const color = score > 0.7 ? "#34C759" : score > 0.4 ? "#FF9500" : "#FF3B30";

  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ transform: "rotate(-90deg)" }}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
      <circle
        cx="50" cy="50" r={r}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeDasharray={circ}
        strokeDashoffset={fill}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1), stroke 0.3s" }}
      />
      <text
        x="50" y="50"
        textAnchor="middle"
        dominantBaseline="central"
        style={{ transform: "rotate(90deg) translate(0px, -100px)", fontSize: "20px", fontWeight: "700", fill: color }}
      >
        {(score * 100).toFixed(0)}%
      </text>
    </svg>
  );
}

// ─── Email card ───────────────────────────────────────────────────────────────
function EmailCard({ email, isActive }) {
  const [expanded, setExpanded] = useState(false);
  const p = PRIORITY_CONFIG[email.priority] || PRIORITY_CONFIG.medium;

  return (
    <div
      onClick={() => setExpanded(!expanded)}
      style={{
        background: isActive ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.02)",
        border: `1px solid ${isActive ? p.color + "60" : "rgba(255,255,255,0.06)"}`,
        borderLeft: `3px solid ${p.color}`,
        borderRadius: "10px",
        padding: "12px 14px",
        cursor: "pointer",
        transition: "all 0.25s ease",
        marginBottom: "8px",
        animation: isActive ? "pulseCard 2s ease-in-out infinite" : "none",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ fontSize: "16px" }}>{p.icon}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "13px", fontWeight: "600", color: "#fff", truncate: true, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {email.subject}
          </div>
          <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.45)", marginTop: "2px" }}>
            {email.sender}
          </div>
        </div>
        <span style={{
          fontSize: "10px", fontWeight: "700", letterSpacing: "0.08em",
          color: p.color, background: p.bg, padding: "2px 7px", borderRadius: "4px"
        }}>
          {p.label}
        </span>
      </div>
      {expanded && (
        <div style={{ marginTop: "10px", fontSize: "12px", color: "rgba(255,255,255,0.6)", lineHeight: "1.5", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "10px" }}>
          {email.body}
        </div>
      )}
    </div>
  );
}

// ─── Decision panel ───────────────────────────────────────────────────────────
function DecisionPanel({ obs, onSubmit, loading }) {
  const [form, setForm] = useState({
    priority: "medium", category: "other", action: "archive", reply_text: "", notes: ""
  });

  if (!obs || obs.email_id === "DONE") return null;

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: "14px",
      padding: "20px",
      marginTop: "16px",
    }}>
      <div style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.12em", color: "rgba(255,255,255,0.4)", marginBottom: "16px" }}>
        TRIAGE DECISION
      </div>

      {/* Priority */}
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", display: "block", marginBottom: "6px" }}>PRIORITY</label>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {Object.entries(PRIORITY_CONFIG).map(([k, v]) => (
            <button key={k} onClick={() => set("priority", k)} style={{
              padding: "5px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: "700",
              border: `1px solid ${form.priority === k ? v.color : "rgba(255,255,255,0.1)"}`,
              background: form.priority === k ? v.bg : "transparent",
              color: form.priority === k ? v.color : "rgba(255,255,255,0.4)",
              cursor: "pointer", transition: "all 0.15s",
            }}>
              {v.icon} {k.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Category */}
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", display: "block", marginBottom: "6px" }}>CATEGORY</label>
        <select value={form.category} onChange={e => set("category", e.target.value)} style={{
          width: "100%", padding: "8px 12px", borderRadius: "8px",
          background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
          color: "#fff", fontSize: "13px",
        }}>
          {Object.entries(CATEGORY_ICONS).map(([k, icon]) => (
            <option key={k} value={k} style={{ background: "#1a1a2e" }}>
              {icon} {k.replace("_", " ").toUpperCase()}
            </option>
          ))}
        </select>
      </div>

      {/* Action */}
      <div style={{ marginBottom: "14px" }}>
        <label style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", display: "block", marginBottom: "6px" }}>ACTION</label>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {[
            { k: "reply", label: "Reply", color: "#34C759" },
            { k: "archive", label: "Archive", color: "#636366" },
            { k: "escalate", label: "Escalate", color: "#FF9500" },
            { k: "delete", label: "Delete", color: "#FF3B30" },
            { k: "forward", label: "Forward", color: "#007AFF" },
          ].map(({ k, label, color }) => (
            <button key={k} onClick={() => set("action", k)} style={{
              padding: "6px 14px", borderRadius: "7px", fontSize: "12px", fontWeight: "600",
              border: `1px solid ${form.action === k ? color : "rgba(255,255,255,0.1)"}`,
              background: form.action === k ? color + "20" : "transparent",
              color: form.action === k ? color : "rgba(255,255,255,0.4)",
              cursor: "pointer", transition: "all 0.15s",
            }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Reply text */}
      {form.action === "reply" && (
        <div style={{ marginBottom: "12px" }}>
          <label style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", display: "block", marginBottom: "6px" }}>REPLY TEXT</label>
          <textarea
            value={form.reply_text}
            onChange={e => set("reply_text", e.target.value)}
            placeholder="Type your reply..."
            rows={3}
            style={{
              width: "100%", padding: "10px 12px", borderRadius: "8px", fontSize: "13px",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#fff", resize: "none", boxSizing: "border-box", outline: "none",
            }}
          />
        </div>
      )}

      {/* Submit */}
      <button
        onClick={() => onSubmit(form)}
        disabled={loading}
        style={{
          width: "100%", padding: "12px", borderRadius: "10px", fontSize: "14px", fontWeight: "700",
          background: loading ? "rgba(255,255,255,0.1)" : "linear-gradient(135deg, #667eea, #764ba2)",
          color: "#fff", border: "none", cursor: loading ? "not-allowed" : "pointer",
          transition: "all 0.2s", letterSpacing: "0.05em",
          boxShadow: loading ? "none" : "0 4px 20px rgba(102,126,234,0.35)",
        }}
      >
        {loading ? "Processing..." : "Submit Decision →"}
      </button>
    </div>
  );
}

// ─── Reward toast ─────────────────────────────────────────────────────────────
function RewardToast({ reward, show }) {
  if (!show) return null;
  const positive = reward >= 0;
  return (
    <div style={{
      position: "fixed", top: "24px", right: "24px", zIndex: 1000,
      background: positive ? "rgba(52,199,89,0.95)" : "rgba(255,59,48,0.95)",
      color: "#fff", padding: "12px 20px", borderRadius: "12px",
      fontSize: "16px", fontWeight: "800", letterSpacing: "0.02em",
      animation: "slideInRight 0.3s ease-out",
      boxShadow: `0 8px 32px ${positive ? "rgba(52,199,89,0.4)" : "rgba(255,59,48,0.4)"}`,
    }}>
      {positive ? "✓" : "✗"} Reward: {reward >= 0 ? "+" : ""}{reward.toFixed(3)}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [session, setSession] = useState(null);
  const [obs, setObs] = useState(null);
  const [log, setLog] = useState([]);
  const [score, setScore] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [lastReward, setLastReward] = useState(null);
  const [showReward, setShowReward] = useState(false);
  const [task, setTask] = useState("task_medium_triage");
  const [health, setHealth] = useState("checking");

  // Check backend health
  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then(r => r.ok ? setHealth("online") : setHealth("offline"))
      .catch(() => setHealth("offline"));
  }, []);

  const startSession = async () => {
    setLoading(true);
    setError(null);
    setLog([]);
    setDone(false);
    setScore(0);
    try {
      const res = await fetch(`${API_BASE}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: task, num_emails: 10, seed: 42 }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setSession(data.session_id);
      setObs(data.observation);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const submitAction = async (form) => {
    if (!session || !obs) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: session, ...form }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Step failed");
      }
      const data = await res.json();

      // Show reward toast
      setLastReward(data.reward);
      setShowReward(true);
      setTimeout(() => setShowReward(false), 2500);

      // Update log
      setLog(prev => [...prev, {
        subject: obs.subject,
        sender: obs.sender,
        priority: form.priority,
        category: form.category,
        action: form.action,
        reward: data.reward,
        gt: data.info?.ground_truth,
      }]);

      setObs(data.observation);
      setScore(data.observation.current_score);
      if (data.done) setDone(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = { online: "#34C759", offline: "#FF3B30", checking: "#FF9500" }[health];

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a12",
      fontFamily: "'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
      color: "#fff",
    }}>
      <style>{`
        @keyframes pulseCard { 0%,100%{box-shadow:0 0 0 0 rgba(255,149,0,0.2)} 50%{box-shadow:0 0 0 8px rgba(255,149,0,0)} }
        @keyframes slideInRight { from{transform:translateX(120%);opacity:0} to{transform:translateX(0);opacity:1} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        * { box-sizing: border-box; }
        select option { background: #1a1a2e; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>

      <RewardToast reward={lastReward} show={showReward} />

      {/* Header */}
      <div style={{
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "16px 32px",
        display: "flex", alignItems: "center", gap: "16px",
        background: "rgba(255,255,255,0.02)",
        backdropFilter: "blur(10px)",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ fontSize: "20px", fontWeight: "800", letterSpacing: "-0.02em" }}>
          📧 EmailTriage<span style={{ color: "#667eea" }}>Env</span>
        </div>
        <div style={{
          fontSize: "10px", fontWeight: "700", letterSpacing: "0.12em",
          color: "#667eea", background: "rgba(102,126,234,0.12)",
          padding: "3px 8px", borderRadius: "4px",
        }}>OPENENV v1.0</div>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "rgba(255,255,255,0.5)" }}>
          <div style={{ width: "7px", height: "7px", borderRadius: "50%", background: statusColor, boxShadow: `0 0 6px ${statusColor}` }} />
          API {health}
        </div>
      </div>

      {/* Main layout */}
      <div style={{ display: "flex", height: "calc(100vh - 57px)" }}>

        {/* Left sidebar - controls */}
        <div style={{
          width: "340px", minWidth: "340px",
          borderRight: "1px solid rgba(255,255,255,0.06)",
          overflowY: "auto", padding: "20px",
        }}>
          {/* Score ring */}
          <div style={{ textAlign: "center", marginBottom: "20px" }}>
            <ScoreRing score={score} size={120} />
            <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", marginTop: "4px" }}>
              Current Score
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "16px" }}>
            {[
              { label: "Processed", value: log.length },
              { label: "Remaining", value: obs?.inbox_count ?? "—" },
              { label: "Step", value: obs?.step_number ?? 0 },
              { label: "Score", value: score, decimals: 3 },
            ].map(({ label, value, decimals }) => (
              <div key={label} style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "10px", padding: "12px",
                textAlign: "center",
              }}>
                <div style={{ fontSize: "20px", fontWeight: "800", color: "#fff" }}>
                  {typeof value === "number" ? <AnimatedNumber value={value} decimals={decimals || 0} /> : value}
                </div>
                <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.4)", marginTop: "2px", letterSpacing: "0.08em" }}>
                  {label.toUpperCase()}
                </div>
              </div>
            ))}
          </div>

          {/* Task selector */}
          <div style={{ marginBottom: "12px" }}>
            <label style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)", display: "block", marginBottom: "6px", letterSpacing: "0.08em" }}>TASK</label>
            <select value={task} onChange={e => setTask(e.target.value)} disabled={!!session && !done} style={{
              width: "100%", padding: "9px 12px", borderRadius: "8px",
              background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
              color: "#fff", fontSize: "13px",
            }}>
              <option value="task_easy_spam">🟢 Easy — Spam Detection</option>
              <option value="task_medium_triage">🟡 Medium — Full Triage</option>
              <option value="task_hard_ambiguous">🔴 Hard — Ambiguous Cases</option>
            </select>
          </div>

          {/* Start button */}
          <button
            onClick={startSession}
            disabled={loading}
            style={{
              width: "100%", padding: "12px", borderRadius: "10px", fontSize: "13px",
              fontWeight: "700", border: "none", cursor: loading ? "not-allowed" : "pointer",
              background: done || !session
                ? "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
                : "rgba(255,255,255,0.06)",
              color: "#fff", transition: "all 0.2s",
              boxShadow: (done || !session) ? "0 4px 16px rgba(102,126,234,0.3)" : "none",
              marginBottom: "8px",
            }}
          >
            {!session ? "▶ Start Session" : done ? "↺ New Session" : "↺ Restart"}
          </button>

          {error && (
            <div style={{
              padding: "10px 12px", borderRadius: "8px",
              background: "rgba(255,59,48,0.1)", border: "1px solid rgba(255,59,48,0.2)",
              color: "#FF3B30", fontSize: "12px", marginTop: "8px",
            }}>
              ⚠ {error}
            </div>
          )}
        </div>

        {/* Center - current email + decision */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px" }}>
          {!session && (
            <div style={{ textAlign: "center", paddingTop: "80px", color: "rgba(255,255,255,0.3)" }}>
              <div style={{ fontSize: "56px", marginBottom: "16px" }}>📬</div>
              <div style={{ fontSize: "20px", fontWeight: "700", color: "rgba(255,255,255,0.6)" }}>
                Email Triage Environment
              </div>
              <div style={{ fontSize: "14px", marginTop: "8px", lineHeight: "1.6", maxWidth: "380px", margin: "12px auto 0" }}>
                An OpenEnv-compliant environment for training AI agents on real-world email management tasks.
              </div>
              <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "32px", flexWrap: "wrap" }}>
                {[
                  { label: "3 Tasks", sub: "Easy → Hard" },
                  { label: "13 Emails", sub: "Mixed difficulty" },
                  { label: "OpenEnv", sub: "Spec compliant" },
                ].map(({ label, sub }) => (
                  <div key={label} style={{
                    background: "rgba(102,126,234,0.08)", border: "1px solid rgba(102,126,234,0.2)",
                    borderRadius: "10px", padding: "14px 20px", minWidth: "100px",
                  }}>
                    <div style={{ fontSize: "16px", fontWeight: "800", color: "#667eea" }}>{label}</div>
                    <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", marginTop: "2px" }}>{sub}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {done && (
            <div style={{
              background: "rgba(52,199,89,0.06)", border: "1px solid rgba(52,199,89,0.2)",
              borderRadius: "14px", padding: "28px", textAlign: "center", marginBottom: "20px",
              animation: "fadeIn 0.4s ease-out",
            }}>
              <div style={{ fontSize: "40px", marginBottom: "12px" }}>🎯</div>
              <div style={{ fontSize: "22px", fontWeight: "800", color: "#34C759" }}>Episode Complete!</div>
              <div style={{ fontSize: "36px", fontWeight: "900", color: "#fff", margin: "12px 0" }}>
                {(score * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.5)" }}>
                Processed {log.length} emails
              </div>
            </div>
          )}

          {/* Current email */}
          {obs && obs.email_id !== "DONE" && (
            <div style={{ animation: "fadeIn 0.3s ease-out" }}>
              <div style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.12em", color: "rgba(255,255,255,0.35)", marginBottom: "12px" }}>
                CURRENT EMAIL — {obs.step_number + 1} of {obs.inbox_count + obs.processed_count}
              </div>

              <div style={{
                background: "rgba(102,126,234,0.06)",
                border: "1px solid rgba(102,126,234,0.2)",
                borderRadius: "14px", padding: "20px",
              }}>
                <div style={{ fontSize: "17px", fontWeight: "700", color: "#fff", marginBottom: "6px" }}>
                  {obs.subject}
                </div>
                <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", marginBottom: "14px", display: "flex", gap: "16px", flexWrap: "wrap" }}>
                  <span>From: <span style={{ color: "rgba(255,255,255,0.7)" }}>{obs.sender}</span></span>
                  <span>Thread: <span style={{ color: "rgba(255,255,255,0.7)" }}>{obs.thread_length} msgs</span></span>
                  {obs.has_attachment && <span style={{ color: "#667eea" }}>📎 Attachment</span>}
                </div>
                <div style={{
                  fontSize: "14px", lineHeight: "1.65", color: "rgba(255,255,255,0.75)",
                  background: "rgba(255,255,255,0.03)", borderRadius: "8px", padding: "14px",
                  borderLeft: "2px solid rgba(102,126,234,0.3)",
                }}>
                  {obs.body}
                </div>
              </div>

              <DecisionPanel obs={obs} onSubmit={submitAction} loading={loading} />
            </div>
          )}
        </div>

        {/* Right sidebar - history */}
        <div style={{
          width: "300px", minWidth: "300px",
          borderLeft: "1px solid rgba(255,255,255,0.06)",
          overflowY: "auto", padding: "20px",
        }}>
          <div style={{ fontSize: "11px", fontWeight: "700", letterSpacing: "0.12em", color: "rgba(255,255,255,0.35)", marginBottom: "14px" }}>
            DECISION LOG
          </div>

          {log.length === 0 && (
            <div style={{ color: "rgba(255,255,255,0.2)", fontSize: "13px", textAlign: "center", marginTop: "32px" }}>
              No decisions yet
            </div>
          )}

          {[...log].reverse().map((entry, i) => {
            const p = PRIORITY_CONFIG[entry.priority] || PRIORITY_CONFIG.medium;
            const positive = entry.reward >= 0;
            return (
              <div key={i} style={{
                background: "rgba(255,255,255,0.02)",
                border: `1px solid rgba(255,255,255,0.05)`,
                borderLeft: `2px solid ${p.color}`,
                borderRadius: "8px", padding: "10px 12px",
                marginBottom: "7px", fontSize: "12px",
                animation: i === 0 ? "fadeIn 0.3s ease-out" : "none",
              }}>
                <div style={{ fontWeight: "600", color: "#fff", marginBottom: "3px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {entry.subject}
                </div>
                <div style={{ display: "flex", gap: "6px", alignItems: "center", flexWrap: "wrap" }}>
                  <span style={{ color: p.color, fontSize: "10px", fontWeight: "700" }}>{entry.priority.toUpperCase()}</span>
                  <span style={{ color: "rgba(255,255,255,0.3)", fontSize: "10px" }}>→ {entry.action}</span>
                  <span style={{ marginLeft: "auto", fontWeight: "800", fontSize: "11px", color: positive ? "#34C759" : "#FF3B30" }}>
                    {positive ? "+" : ""}{entry.reward?.toFixed(3)}
                  </span>
                </div>
                {entry.gt && (
                  <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.3)", marginTop: "4px" }}>
                    GT: {entry.gt.priority} / {entry.gt.action}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
