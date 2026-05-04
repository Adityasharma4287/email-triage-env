import { useState, useEffect, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";

const PRIORITY_CONFIG = {
  urgent: { color: "#FF3B30", bg: "#FF3B3015", label: "URGENT", icon: "⚡" },
  high:   { color: "#FF9500", bg: "#FF950015", label: "HIGH",   icon: "🔺" },
  medium: { color: "#34C759", bg: "#34C75915", label: "MEDIUM", icon: "◆" },
  low:    { color: "#636366", bg: "#63636615", label: "LOW",    icon: "▼" },
  spam:   { color: "#FF453A", bg: "#FF453A15", label: "SPAM",   icon: "🚫" },
};

const CATEGORY_ICONS = {
  customer_support:"👤", billing:"💳", technical:"⚙️", sales:"📈",
  internal:"🏢", spam:"⛔", legal:"⚖️", hr:"👥", other:"📌",
};

const ACTION_CONFIG = {
  reply:    { color:"#34C759", label:"Reply" },
  archive:  { color:"#636366", label:"Archive" },
  escalate: { color:"#FF9500", label:"Escalate" },
  delete:   { color:"#FF3B30", label:"Delete" },
  forward:  { color:"#007AFF", label:"Forward" },
  snooze:   { color:"#AF52DE", label:"Snooze" },
};

const CUSTOM_TAGS = ["VIP", "follow-up", "legal-review", "churn-risk", "high-value", "phishing"];

function AnimatedNumber({ value, decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    const start = display, end = value, duration = 600, startTime = performance.now();
    const animate = (now) => {
      const p = Math.min((now - startTime)/duration, 1);
      const ease = 1-Math.pow(1-p,3);
      const cur = start+(end-start)*ease;
      setDisplay(decimals>0 ? parseFloat(cur.toFixed(decimals)) : Math.round(cur));
      if(p<1) ref.current = requestAnimationFrame(animate);
    };
    ref.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(ref.current);
  }, [value]);
  return <span>{decimals>0 ? display.toFixed(decimals) : display}</span>;
}

function ScoreRing({ score, size=120 }) {
  const r=46, circ=2*Math.PI*r, fill=circ*(1-score);
  const color = score>0.7?"#34C759":score>0.4?"#FF9500":"#FF3B30";
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{transform:"rotate(-90deg)"}}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8"/>
      <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={circ} strokeDashoffset={fill} strokeLinecap="round"
        style={{transition:"stroke-dashoffset 0.8s cubic-bezier(0.4,0,0.2,1),stroke 0.3s"}}/>
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central"
        style={{transform:"rotate(90deg) translate(0px,-100px)",fontSize:"20px",fontWeight:"700",fill:color}}>
        {(score*100).toFixed(0)}%
      </text>
    </svg>
  );
}

function SentimentBar({ value }) {
  const pct = (value+1)/2*100;
  const color = value<-0.5?"#FF3B30":value>0.5?"#34C759":"#FF9500";
  const label = value<-0.6?"😡 Very Angry":value<-0.2?"😤 Frustrated":value<0.2?"😐 Neutral":value<0.6?"🙂 Positive":"😊 Happy";
  return (
    <div style={{marginTop:4}}>
      <div style={{display:"flex",justifyContent:"space-between",fontSize:10,color:"rgba(255,255,255,0.4)",marginBottom:3}}>
        <span>Sentiment</span><span style={{color}}>{label}</span>
      </div>
      <div style={{background:"rgba(255,255,255,0.06)",borderRadius:4,height:4,overflow:"hidden"}}>
        <div style={{width:`${pct}%`,height:"100%",background:color,borderRadius:4,transition:"width 0.4s ease"}}/>
      </div>
    </div>
  );
}

function SLABadge({ slaHours }) {
  if (!slaHours) return null;
  const urgent = slaHours <= 4;
  const color = slaHours<=2?"#FF3B30":slaHours<=8?"#FF9500":"#34C759";
  return (
    <span style={{display:"inline-flex",alignItems:"center",gap:4,padding:"2px 8px",borderRadius:4,
      background:`${color}20`,border:`1px solid ${color}40`,fontSize:10,color,fontWeight:700}}>
      ⏱ SLA: {slaHours}h
    </span>
  );
}

function DecisionPanel({ obs, onSubmit, loading }) {
  const [form, setForm] = useState({
    priority:"medium",category:"other",action:"archive",reply_text:"",
    forward_to:"",notes:"",custom_tags:[],snooze_hours:4
  });
  if(!obs || obs.email_id==="DONE") return null;
  const set = (k,v) => setForm(f=>({...f,[k]:v}));
  const toggleTag = (tag) => {
    setForm(f=>({...f, custom_tags: f.custom_tags.includes(tag)
      ? f.custom_tags.filter(t=>t!==tag)
      : [...f.custom_tags, tag]}));
  };
  return (
    <div style={{background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:14,padding:20,marginTop:16}}>
      <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.12em",color:"rgba(255,255,255,0.4)",marginBottom:16}}>TRIAGE DECISION</div>

      {/* Priority */}
      <div style={{marginBottom:12}}>
        <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>PRIORITY</label>
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          {Object.entries(PRIORITY_CONFIG).map(([k,v])=>(
            <button key={k} onClick={()=>set("priority",k)} style={{
              padding:"5px 12px",borderRadius:6,fontSize:11,fontWeight:700,
              border:`1px solid ${form.priority===k?v.color:"rgba(255,255,255,0.1)"}`,
              background:form.priority===k?v.bg:"transparent",
              color:form.priority===k?v.color:"rgba(255,255,255,0.4)",cursor:"pointer",transition:"all 0.15s",
            }}>{v.icon} {k.toUpperCase()}</button>
          ))}
        </div>
      </div>

      {/* Category */}
      <div style={{marginBottom:12}}>
        <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>CATEGORY</label>
        <select value={form.category} onChange={e=>set("category",e.target.value)} style={{
          width:"100%",padding:"8px 12px",borderRadius:8,
          background:"rgba(255,255,255,0.06)",border:"1px solid rgba(255,255,255,0.1)",
          color:"#fff",fontSize:13,
        }}>
          {Object.entries(CATEGORY_ICONS).map(([k,icon])=>(
            <option key={k} value={k} style={{background:"#1a1a2e"}}>{icon} {k.replace(/_/g," ").toUpperCase()}</option>
          ))}
        </select>
      </div>

      {/* Action */}
      <div style={{marginBottom:12}}>
        <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>ACTION</label>
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          {Object.entries(ACTION_CONFIG).map(([k,v])=>(
            <button key={k} onClick={()=>set("action",k)} style={{
              padding:"6px 14px",borderRadius:7,fontSize:12,fontWeight:600,
              border:`1px solid ${form.action===k?v.color:"rgba(255,255,255,0.1)"}`,
              background:form.action===k?v.color+"20":"transparent",
              color:form.action===k?v.color:"rgba(255,255,255,0.4)",cursor:"pointer",transition:"all 0.15s",
            }}>{v.label}</button>
          ))}
        </div>
      </div>

      {/* Snooze hours */}
      {form.action==="snooze" && (
        <div style={{marginBottom:12}}>
          <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>SNOOZE DURATION</label>
          <div style={{display:"flex",gap:6}}>
            {[1,4,8,24,48].map(h=>(
              <button key={h} onClick={()=>set("snooze_hours",h)} style={{
                padding:"4px 12px",borderRadius:6,fontSize:12,fontWeight:600,
                border:`1px solid ${form.snooze_hours===h?"#AF52DE":"rgba(255,255,255,0.1)"}`,
                background:form.snooze_hours===h?"#AF52DE20":"transparent",
                color:form.snooze_hours===h?"#AF52DE":"rgba(255,255,255,0.4)",cursor:"pointer",
              }}>{h}h</button>
            ))}
          </div>
        </div>
      )}

      {/* Reply text */}
      {form.action==="reply" && (
        <div style={{marginBottom:12}}>
          <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>REPLY TEXT</label>
          <textarea value={form.reply_text} onChange={e=>set("reply_text",e.target.value)}
            placeholder="Type your reply..." rows={3} style={{
              width:"100%",padding:"10px 12px",borderRadius:8,fontSize:13,
              background:"rgba(255,255,255,0.06)",border:"1px solid rgba(255,255,255,0.1)",
              color:"#fff",resize:"none",boxSizing:"border-box",outline:"none",
            }}/>
        </div>
      )}

      {/* Forward to */}
      {form.action==="forward" && (
        <div style={{marginBottom:12}}>
          <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>FORWARD TO</label>
          <input value={form.forward_to} onChange={e=>set("forward_to",e.target.value)}
            placeholder="team@company.com" style={{
              width:"100%",padding:"8px 12px",borderRadius:8,fontSize:13,
              background:"rgba(255,255,255,0.06)",border:"1px solid rgba(255,255,255,0.1)",
              color:"#fff",outline:"none",boxSizing:"border-box",
            }}/>
        </div>
      )}

      {/* Custom Tags — NEW */}
      <div style={{marginBottom:14}}>
        <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>CUSTOM TAGS (optional)</label>
        <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
          {CUSTOM_TAGS.map(tag=>{
            const active = form.custom_tags.includes(tag);
            return (
              <button key={tag} onClick={()=>toggleTag(tag)} style={{
                padding:"3px 10px",borderRadius:12,fontSize:11,fontWeight:600,
                border:`1px solid ${active?"#667eea":"rgba(255,255,255,0.1)"}`,
                background:active?"rgba(102,126,234,0.2)":"transparent",
                color:active?"#667eea":"rgba(255,255,255,0.35)",cursor:"pointer",transition:"all 0.15s",
              }}>#{tag}</button>
            );
          })}
        </div>
      </div>

      <button onClick={()=>onSubmit(form)} disabled={loading} style={{
        width:"100%",padding:12,borderRadius:10,fontSize:14,fontWeight:700,
        background:loading?"rgba(255,255,255,0.1)":"linear-gradient(135deg,#667eea,#764ba2)",
        color:"#fff",border:"none",cursor:loading?"not-allowed":"pointer",
        transition:"all 0.2s",letterSpacing:"0.05em",
        boxShadow:loading?"none":"0 4px 20px rgba(102,126,234,0.35)",
      }}>{loading?"Processing...":"Submit Decision →"}</button>
    </div>
  );
}

function RewardToast({ reward, show }) {
  if(!show) return null;
  const positive = reward>=0;
  return (
    <div style={{position:"fixed",top:24,right:24,zIndex:1000,
      background:positive?"rgba(52,199,89,0.95)":"rgba(255,59,48,0.95)",
      color:"#fff",padding:"12px 20px",borderRadius:12,fontSize:16,fontWeight:800,
      animation:"slideInRight 0.3s ease-out",
      boxShadow:`0 8px 32px ${positive?"rgba(52,199,89,0.4)":"rgba(255,59,48,0.4)"}`}}>
      {positive?"✓":"✗"} {reward>=0?"+":""}{reward.toFixed(3)}
    </div>
  );
}

function AnalyticsPanel({ sessionId, show }) {
  const [data, setData] = useState(null);
  const [tab, setTab] = useState("overview");
  useEffect(()=>{
    if(!show||!sessionId) return;
    fetch(`${API_BASE}/analytics/${sessionId}`)
      .then(r=>r.json()).then(setData).catch(()=>{});
  }, [show, sessionId]);
  if(!show||!data) return null;
  return (
    <div style={{background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:14,padding:20,marginTop:16}}>
      <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.12em",color:"rgba(255,255,255,0.4)",marginBottom:12}}>ANALYTICS</div>
      <div style={{display:"flex",gap:8,marginBottom:14}}>
        {["overview","accuracy","mistakes"].map(t=>(
          <button key={t} onClick={()=>setTab(t)} style={{
            padding:"4px 12px",borderRadius:6,fontSize:11,fontWeight:700,
            background:tab===t?"rgba(102,126,234,0.2)":"transparent",
            border:`1px solid ${tab===t?"#667eea":"rgba(255,255,255,0.1)"}`,
            color:tab===t?"#667eea":"rgba(255,255,255,0.4)",cursor:"pointer",
          }}>{t.toUpperCase()}</button>
        ))}
      </div>
      {tab==="overview" && (
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>
          {[
            {label:"Score",value:`${(data.overall_score*100).toFixed(1)}%`,color:"#34C759"},
            {label:"Perfect",value:data.perfect_decisions,color:"#007AFF"},
            {label:"Mistakes",value:data.mistake_count,color:"#FF3B30"},
            {label:"Avg Reward",value:data.average_reward,color:"#FF9500"},
            {label:"SLA Breaches",value:data.sla_breaches,color:"#FF3B30"},
            {label:"Tags Used",value:data.total_tags_used,color:"#AF52DE"},
          ].map(({label,value,color})=>(
            <div key={label} style={{background:"rgba(255,255,255,0.03)",borderRadius:8,padding:"10px 12px",textAlign:"center"}}>
              <div style={{fontSize:18,fontWeight:800,color}}>{value}</div>
              <div style={{fontSize:10,color:"rgba(255,255,255,0.4)",marginTop:2}}>{label}</div>
            </div>
          ))}
        </div>
      )}
      {tab==="accuracy" && (
        <div>
          {[["Priority",data.priority_accuracy],["Category",data.category_accuracy],["Action",data.action_accuracy]].map(([title,stats])=>(
            <div key={title} style={{marginBottom:12}}>
              <div style={{fontSize:11,color:"rgba(255,255,255,0.5)",marginBottom:6,fontWeight:700}}>{title.toUpperCase()}</div>
              {Object.entries(stats||{}).map(([k,v])=>(
                <div key={k} style={{display:"flex",alignItems:"center",gap:8,marginBottom:4}}>
                  <span style={{fontSize:11,color:"rgba(255,255,255,0.6)",width:100,flexShrink:0}}>{k}</span>
                  <div style={{flex:1,background:"rgba(255,255,255,0.06)",borderRadius:4,height:6,overflow:"hidden"}}>
                    <div style={{width:`${v.accuracy*100}%`,height:"100%",background:v.accuracy>0.7?"#34C759":v.accuracy>0.4?"#FF9500":"#FF3B30",borderRadius:4,transition:"width 0.5s ease"}}/>
                  </div>
                  <span style={{fontSize:11,color:"rgba(255,255,255,0.6)",width:36,textAlign:"right"}}>{(v.accuracy*100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
      {tab==="mistakes" && (
        <div>
          {(data.mistakes||[]).length===0
            ? <div style={{color:"rgba(255,255,255,0.3)",fontSize:13,textAlign:"center"}}>No mistakes! 🎉</div>
            : (data.mistakes||[]).map((m,i)=>(
              <div key={i} style={{background:"rgba(255,59,48,0.06)",border:"1px solid rgba(255,59,48,0.15)",borderRadius:8,padding:"10px 12px",marginBottom:6}}>
                <div style={{fontSize:12,color:"#fff",fontWeight:600,marginBottom:4}}>{m.subject}</div>
                <div style={{display:"flex",gap:12,fontSize:11,color:"rgba(255,255,255,0.5)"}}>
                  <span>Your: <span style={{color:"#FF3B30"}}>{m.agent_priority}/{m.agent_action}</span></span>
                  <span>Correct: <span style={{color:"#34C759"}}>{m.gt_priority}/{m.gt_action}</span></span>
                  <span style={{marginLeft:"auto",color:"#FF3B30",fontWeight:700}}>{m.reward.toFixed(3)}</span>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

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
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [difficultyRamp, setDifficultyRamp] = useState(false);
  const [numEmails, setNumEmails] = useState(10);

  useEffect(()=>{
    fetch(`${API_BASE}/health`)
      .then(r=>r.ok?setHealth("online"):setHealth("offline"))
      .catch(()=>setHealth("offline"));
  },[]);

  const startSession = async() => {
    setLoading(true); setError(null); setLog([]); setDone(false); setScore(0); setShowAnalytics(false);
    try {
      const res = await fetch(`${API_BASE}/reset`,{
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({task_id:task, num_emails:numEmails, seed:42, difficulty_ramp:difficultyRamp}),
      });
      if(!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setSession(data.session_id); setObs(data.observation);
    } catch(e){ setError(e.message); }
    finally { setLoading(false); }
  };

  const submitAction = async(form) => {
    if(!session||!obs) return;
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/step`,{
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({session_id:session, ...form}),
      });
      if(!res.ok){ const e=await res.json(); throw new Error(e.detail||"Step failed"); }
      const data = await res.json();
      setLastReward(data.reward); setShowReward(true);
      setTimeout(()=>setShowReward(false), 2500);
      setLog(prev=>[...prev,{
        subject:obs.subject, sender:obs.sender, priority:form.priority, category:form.category,
        action:form.action, reward:data.reward, gt:data.info?.ground_truth,
        tags:form.custom_tags, sentiment:obs.sentiment_score, sla:obs.sla_hours,
      }]);
      setObs(data.observation); setScore(data.observation.current_score);
      if(data.done){ setDone(true); setShowAnalytics(true); }
    } catch(e){ setError(e.message); }
    finally { setLoading(false); }
  };

  const statusColor = {online:"#34C759",offline:"#FF3B30",checking:"#FF9500"}[health];

  return (
    <div style={{minHeight:"100vh",background:"#0a0a12",fontFamily:"'SF Pro Display',-apple-system,BlinkMacSystemFont,sans-serif",color:"#fff"}}>
      <style>{`
        @keyframes pulseCard{0%,100%{box-shadow:0 0 0 0 rgba(255,149,0,0.2)}50%{box-shadow:0 0 0 8px rgba(255,149,0,0)}}
        @keyframes slideInRight{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}
        @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
        *{box-sizing:border-box} select option{background:#1a1a2e}
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:2px}
        input,textarea{caret-color:#667eea}
      `}</style>
      <RewardToast reward={lastReward} show={showReward}/>

      {/* Header */}
      <div style={{borderBottom:"1px solid rgba(255,255,255,0.06)",padding:"16px 32px",display:"flex",alignItems:"center",gap:16,background:"rgba(255,255,255,0.02)",backdropFilter:"blur(10px)",position:"sticky",top:0,zIndex:100}}>
        <div style={{fontSize:20,fontWeight:800,letterSpacing:"-0.02em"}}>📧 EmailTriage<span style={{color:"#667eea"}}>Env</span></div>
        <div style={{fontSize:10,fontWeight:700,letterSpacing:"0.12em",color:"#667eea",background:"rgba(102,126,234,0.12)",padding:"3px 8px",borderRadius:4}}>v2.0 ADVANCED</div>
        <div style={{flex:1}}/>
        <div style={{display:"flex",alignItems:"center",gap:6,fontSize:12,color:"rgba(255,255,255,0.5)"}}>
          <div style={{width:7,height:7,borderRadius:"50%",background:statusColor,boxShadow:`0 0 6px ${statusColor}`}}/>
          API {health}
        </div>
      </div>

      {/* Main */}
      <div style={{display:"flex",height:"calc(100vh - 57px)"}}>

        {/* Left sidebar */}
        <div style={{width:340,minWidth:340,borderRight:"1px solid rgba(255,255,255,0.06)",overflowY:"auto",padding:20}}>
          <div style={{textAlign:"center",marginBottom:20}}>
            <ScoreRing score={score} size={120}/>
            <div style={{fontSize:12,color:"rgba(255,255,255,0.4)",marginTop:4}}>Current Score</div>
          </div>

          {/* Stats */}
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:16}}>
            {[{label:"Processed",value:log.length},{label:"Remaining",value:obs?.inbox_count??"—"},
              {label:"Step",value:obs?.step_number??0},{label:"Score",value:score,decimals:3}].map(({label,value,decimals})=>(
              <div key={label} style={{background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.06)",borderRadius:10,padding:12,textAlign:"center"}}>
                <div style={{fontSize:20,fontWeight:800,color:"#fff"}}>
                  {typeof value==="number"?<AnimatedNumber value={value} decimals={decimals||0}/>:value}
                </div>
                <div style={{fontSize:10,color:"rgba(255,255,255,0.4)",marginTop:2,letterSpacing:"0.08em"}}>{label.toUpperCase()}</div>
              </div>
            ))}
          </div>

          {/* Task selector */}
          <div style={{marginBottom:10}}>
            <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6,letterSpacing:"0.08em"}}>TASK</label>
            <select value={task} onChange={e=>setTask(e.target.value)} disabled={!!session&&!done} style={{width:"100%",padding:"9px 12px",borderRadius:8,background:"rgba(255,255,255,0.06)",border:"1px solid rgba(255,255,255,0.1)",color:"#fff",fontSize:13}}>
              <option value="task_easy_spam">🟢 Easy — Spam Detection</option>
              <option value="task_medium_triage">🟡 Medium — Full Triage</option>
              <option value="task_hard_ambiguous">🔴 Hard — Ambiguous</option>
            </select>
          </div>

          {/* Email count */}
          <div style={{marginBottom:10}}>
            <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",display:"block",marginBottom:6}}>EMAILS: {numEmails}</label>
            <input type="range" min={5} max={25} value={numEmails} onChange={e=>setNumEmails(+e.target.value)}
              disabled={!!session&&!done}
              style={{width:"100%",accentColor:"#667eea"}}/>
          </div>

          {/* Difficulty ramp toggle */}
          <div style={{marginBottom:12,display:"flex",alignItems:"center",gap:10}}>
            <label style={{fontSize:11,color:"rgba(255,255,255,0.5)",cursor:"pointer",display:"flex",alignItems:"center",gap:8}}>
              <div onClick={()=>!(session&&!done)&&setDifficultyRamp(r=>!r)} style={{
                width:32,height:18,borderRadius:9,background:difficultyRamp?"#667eea":"rgba(255,255,255,0.15)",
                position:"relative",cursor:(session&&!done)?"not-allowed":"pointer",transition:"background 0.2s",
              }}>
                <div style={{position:"absolute",top:2,left:difficultyRamp?14:2,width:14,height:14,
                  borderRadius:"50%",background:"#fff",transition:"left 0.2s"}}/>
              </div>
              Difficulty Ramp ✨
            </label>
          </div>

          <button onClick={startSession} disabled={loading} style={{
            width:"100%",padding:12,borderRadius:10,fontSize:13,fontWeight:700,border:"none",
            cursor:loading?"not-allowed":"pointer",
            background:(done||!session)?"linear-gradient(135deg,#667eea 0%,#764ba2 100%)":"rgba(255,255,255,0.06)",
            color:"#fff",transition:"all 0.2s",
            boxShadow:(done||!session)?"0 4px 16px rgba(102,126,234,0.3)":"none",marginBottom:8,
          }}>
            {!session?"▶ Start Session":done?"↺ New Session":"↺ Restart"}
          </button>

          {session && (
            <button onClick={()=>setShowAnalytics(s=>!s)} style={{
              width:"100%",padding:8,borderRadius:8,fontSize:12,fontWeight:600,border:"1px solid rgba(102,126,234,0.3)",
              background:showAnalytics?"rgba(102,126,234,0.15)":"transparent",color:"#667eea",cursor:"pointer",
            }}>📊 {showAnalytics?"Hide":"Show"} Analytics</button>
          )}

          {error && (<div style={{padding:"10px 12px",borderRadius:8,background:"rgba(255,59,48,0.1)",border:"1px solid rgba(255,59,48,0.2)",color:"#FF3B30",fontSize:12,marginTop:8}}>⚠ {error}</div>)}
        </div>

        {/* Center */}
        <div style={{flex:1,overflowY:"auto",padding:"24px 28px"}}>
          {!session && (
            <div style={{textAlign:"center",paddingTop:80,color:"rgba(255,255,255,0.3)"}}>
              <div style={{fontSize:56,marginBottom:16}}>📬</div>
              <div style={{fontSize:20,fontWeight:700,color:"rgba(255,255,255,0.6)"}}>Email Triage Environment v2.0</div>
              <div style={{fontSize:14,marginTop:8,lineHeight:1.6,maxWidth:420,margin:"12px auto 0"}}>
                Advanced OpenEnv with SLA tracking, sentiment analysis, custom tags, snooze action & more.
              </div>
              <div style={{display:"flex",gap:12,justifyContent:"center",marginTop:32,flexWrap:"wrap"}}>
                {[{label:"SLA Tracking",icon:"⏱"},{label:"Sentiment AI",icon:"🧠"},{label:"Custom Tags",icon:"🏷️"},
                  {label:"Snooze Action",icon:"💤"},{label:"Legal/HR",icon:"⚖️"},{label:"Difficulty Ramp",icon:"📈"}].map(({label,icon})=>(
                  <div key={label} style={{background:"rgba(102,126,234,0.08)",border:"1px solid rgba(102,126,234,0.2)",borderRadius:10,padding:"12px 16px",minWidth:100}}>
                    <div style={{fontSize:20}}>{icon}</div>
                    <div style={{fontSize:11,color:"rgba(255,255,255,0.5)",marginTop:4}}>{label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {done && (
            <div style={{background:"rgba(52,199,89,0.06)",border:"1px solid rgba(52,199,89,0.2)",borderRadius:14,padding:28,textAlign:"center",marginBottom:20,animation:"fadeIn 0.4s ease-out"}}>
              <div style={{fontSize:40,marginBottom:12}}>🎯</div>
              <div style={{fontSize:22,fontWeight:800,color:"#34C759"}}>Episode Complete!</div>
              <div style={{fontSize:36,fontWeight:900,color:"#fff",margin:"12px 0"}}>{(score*100).toFixed(1)}%</div>
              <div style={{fontSize:13,color:"rgba(255,255,255,0.5)"}}>Processed {log.length} emails</div>
            </div>
          )}

          {obs && obs.email_id!=="DONE" && (
            <div style={{animation:"fadeIn 0.3s ease-out"}}>
              <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.12em",color:"rgba(255,255,255,0.35)",marginBottom:12}}>
                CURRENT EMAIL — {obs.step_number+1} of {obs.inbox_count+obs.processed_count}
              </div>
              <div style={{background:"rgba(102,126,234,0.06)",border:"1px solid rgba(102,126,234,0.2)",borderRadius:14,padding:20}}>
                <div style={{display:"flex",alignItems:"flex-start",gap:10,marginBottom:8}}>
                  <div style={{flex:1}}>
                    <div style={{fontSize:17,fontWeight:700,color:"#fff",marginBottom:4}}>{obs.subject}</div>
                    <div style={{fontSize:12,color:"rgba(255,255,255,0.4)",display:"flex",gap:12,flexWrap:"wrap",alignItems:"center"}}>
                      <span>From: <span style={{color:"rgba(255,255,255,0.7)"}}>{obs.sender}</span></span>
                      <span>Thread: {obs.thread_length} msgs</span>
                      {obs.has_attachment && <span style={{color:"#667eea"}}>📎 {obs.attachment_type||"File"}</span>}
                      {obs.language!=="en" && <span style={{color:"#FF9500"}}>🌐 {obs.language.toUpperCase()}</span>}
                      <SLABadge slaHours={obs.sla_hours}/>
                    </div>
                  </div>
                  <div style={{fontSize:10,fontWeight:700,padding:"3px 8px",borderRadius:4,
                    background:obs.difficulty==="hard"?"rgba(255,59,48,0.15)":obs.difficulty==="medium"?"rgba(255,149,0,0.15)":"rgba(52,199,89,0.15)",
                    color:obs.difficulty==="hard"?"#FF3B30":obs.difficulty==="medium"?"#FF9500":"#34C759"}}>
                    {obs.difficulty.toUpperCase()}
                  </div>
                </div>
                <SentimentBar value={obs.sentiment_score}/>
                <div style={{fontSize:14,lineHeight:1.65,color:"rgba(255,255,255,0.75)",background:"rgba(255,255,255,0.03)",borderRadius:8,padding:14,borderLeft:"2px solid rgba(102,126,234,0.3)",marginTop:12}}>
                  {obs.body}
                </div>
              </div>
              <DecisionPanel obs={obs} onSubmit={submitAction} loading={loading}/>
            </div>
          )}

          <AnalyticsPanel sessionId={session} show={showAnalytics}/>
        </div>

        {/* Right sidebar — decision log */}
        <div style={{width:300,minWidth:300,borderLeft:"1px solid rgba(255,255,255,0.06)",overflowY:"auto",padding:20}}>
          <div style={{fontSize:11,fontWeight:700,letterSpacing:"0.12em",color:"rgba(255,255,255,0.35)",marginBottom:14}}>DECISION LOG</div>
          {log.length===0 && <div style={{color:"rgba(255,255,255,0.2)",fontSize:13,textAlign:"center",marginTop:32}}>No decisions yet</div>}
          {[...log].reverse().map((entry,i)=>{
            const p = PRIORITY_CONFIG[entry.priority]||PRIORITY_CONFIG.medium;
            const positive = entry.reward>=0;
            return (
              <div key={i} style={{background:"rgba(255,255,255,0.02)",border:"1px solid rgba(255,255,255,0.05)",borderLeft:`2px solid ${p.color}`,borderRadius:8,padding:"10px 12px",marginBottom:7,fontSize:12,animation:i===0?"fadeIn 0.3s ease-out":"none"}}>
                <div style={{fontWeight:600,color:"#fff",marginBottom:3,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{entry.subject}</div>
                <div style={{display:"flex",gap:6,alignItems:"center",flexWrap:"wrap"}}>
                  <span style={{color:p.color,fontSize:10,fontWeight:700}}>{entry.priority.toUpperCase()}</span>
                  <span style={{color:"rgba(255,255,255,0.3)",fontSize:10}}>→ {entry.action}</span>
                  {entry.tags?.length>0 && <span style={{color:"#667eea",fontSize:9}}>#{entry.tags[0]}</span>}
                  <span style={{marginLeft:"auto",fontWeight:800,fontSize:11,color:positive?"#34C759":"#FF3B30"}}>
                    {positive?"+":""}{entry.reward?.toFixed(3)}
                  </span>
                </div>
                {entry.sentiment!==undefined && <SentimentBar value={entry.sentiment}/>}
                {entry.gt && <div style={{fontSize:10,color:"rgba(255,255,255,0.3)",marginTop:4}}>GT: {entry.gt.priority} / {entry.gt.action}</div>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
