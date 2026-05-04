"""
Email Triage OpenEnv - FastAPI Server ADVANCED v2.0
NEW: SLA, Sentiment, Custom Tags, Snooze, Leaderboard, Analytics
"""
import os, sys, uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from env.email_triage_env import EmailTriageEnv, TriageAction, Priority, Category

app = FastAPI(title="Email Triage OpenEnv v2", version="2.0.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

sessions: dict = {}
session_meta: dict = {}
_leaderboard: list = []

def utcnow(): return datetime.now(timezone.utc).isoformat()

class ResetRequest(BaseModel):
    task_id: str = "task_medium_triage"
    num_emails: int = 10
    seed: int = 42
    difficulty_ramp: bool = False

class StepRequest(BaseModel):
    session_id: str
    priority: str
    category: str
    action: str
    reply_text: Optional[str] = None
    forward_to: Optional[str] = None
    notes: Optional[str] = None
    custom_tags: Optional[list] = None
    snooze_hours: Optional[int] = None

class LeaderboardEntry(BaseModel):
    agent_name: str
    score: float
    task_id: str
    model: Optional[str] = "unknown"
    notes: Optional[str] = None

@app.get("/")
async def root():
    return {"name":"email-triage-openenv-v2","version":"2.0.0","status":"running",
            "new_features":["sla_tracking","sentiment_scoring","custom_tags","snooze_action","difficulty_ramp","legal_hr_categories"],
            "endpoints":["/reset","/step","/state","/score","/analytics","/sentiment","/sla","/leaderboard","/validate","/health","/tasks"]}

@app.get("/health")
async def health():
    return {"status":"ok","timestamp":utcnow(),"sessions":len(sessions),"version":"2.0.0"}

@app.post("/reset")
async def reset_environment(req: Optional[ResetRequest] = None):
    if req is None: req = ResetRequest()
    sid = str(uuid.uuid4())[:8]
    env = EmailTriageEnv(task_id=req.task_id, num_emails=req.num_emails, seed=req.seed, difficulty_ramp=req.difficulty_ramp)
    obs = env.reset()
    sessions[sid] = env
    started_at = utcnow()
    session_meta[sid] = {"task_id":req.task_id,"started_at":started_at,"steps":0,"difficulty_ramp":req.difficulty_ramp}
    return {"session_id":sid,"observation":obs.model_dump(),"task_id":req.task_id,"started_at":started_at}

@app.post("/step")
async def step_environment(req: StepRequest):
    if req.session_id not in sessions: raise HTTPException(404, f"Session '{req.session_id}' not found.")
    env = sessions[req.session_id]
    if env.state().done: raise HTTPException(400, "Episode done. Call /reset.")
    if req.action not in {"reply","archive","escalate","delete","forward","snooze"}:
        raise HTTPException(422, f"Invalid action '{req.action}'")
    try: priority = Priority(req.priority); category = Category(req.category)
    except ValueError as e: raise HTTPException(422, str(e))
    cur = env.current_observation()
    action = TriageAction(email_id=cur.email_id, priority=priority, category=category,
                          action=req.action, reply_text=req.reply_text, forward_to=req.forward_to,
                          notes=req.notes, custom_tags=req.custom_tags or [], snooze_hours=req.snooze_hours)
    obs, reward, done, info = env.step(action)
    session_meta[req.session_id]["steps"] = session_meta[req.session_id].get("steps",0)+1
    return {"observation":obs.model_dump(),"reward":reward,"done":done,"info":info,"session_id":req.session_id}

@app.get("/state/{session_id}")
async def get_state(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    env = sessions[session_id]
    return {**env.state().model_dump(),"score":env.get_score(),"metadata":session_meta.get(session_id,{})}

@app.get("/score/{session_id}")
async def get_score(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    env = sessions[session_id]
    return {"session_id":session_id,"score":env.get_score(),"cumulative_reward":env.cumulative_reward,"done":env.is_done,"steps":env.step_count}

@app.get("/log/{session_id}")
async def get_log(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    return {"session_id":session_id,"log":sessions[session_id].get_episode_log()}

@app.get("/analytics/{session_id}")
async def get_analytics(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    env = sessions[session_id]; log = env.get_episode_log()
    if not log: return {"session_id":session_id,"message":"No steps yet."}
    p_stats,c_stats,a_stats,mistakes = {},{},{},[]
    for e in log:
        gt,ag = e["ground_truth"],e["agent_action"]
        for field,stats in [("priority",p_stats),("category",c_stats),("action",a_stats)]:
            k = gt[field]
            if k not in stats: stats[k]={"correct":0,"total":0}
            stats[k]["total"]+=1
            if ag[field]==gt[field]: stats[k]["correct"]+=1
        if e["reward"]<0:
            mistakes.append({"subject":e.get("subject","")[:60],"gt_priority":gt.get("priority"),
                             "gt_action":gt.get("action"),"agent_priority":ag.get("priority"),
                             "agent_action":ag.get("action"),"reward":round(e["reward"],4)})
    def acc(s): return {k:{"accuracy":round(v["correct"]/v["total"],3) if v["total"] else 0,"correct":v["correct"],"total":v["total"]} for k,v in s.items()}
    state = env.state()
    return {"session_id":session_id,"total_steps":len(log),"overall_score":env.get_score(),
            "average_reward":round(sum(e["reward"] for e in log)/len(log),4),
            "priority_accuracy":acc(p_stats),"category_accuracy":acc(c_stats),"action_accuracy":acc(a_stats),
            "mistakes":mistakes,"mistake_count":len(mistakes),
            "perfect_decisions":sum(1 for e in log if e["reward"]>=0.9),
            "sla_breaches":state.sla_breaches,"total_tags_used":state.total_tags_used,"avg_sentiment":state.avg_sentiment}

@app.get("/sentiment/{session_id}")
async def get_sentiment(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    log = sessions[session_id].get_episode_log()
    if not log: return {"session_id":session_id,"message":"No steps yet."}
    angry = [e for e in log if e.get("sentiment",0)<-0.5]
    positive = [e for e in log if e.get("sentiment",0)>0.5]
    return {"session_id":session_id,"total_emails":len(log),
            "avg_sentiment":round(sum(e.get("sentiment",0) for e in log)/len(log),3),
            "angry_emails":len(angry),"positive_emails":len(positive),
            "angry_correctly_handled":sum(1 for e in angry if e["agent_action"]["action"] in ("escalate","reply")),
            "most_angry":[{"subject":e.get("subject","")[:50],"sentiment":e.get("sentiment")} for e in sorted(angry,key=lambda x:x.get("sentiment",0))[:3]]}

@app.get("/sla/{session_id}")
async def get_sla(session_id: str):
    if session_id not in sessions: raise HTTPException(404, "Not found.")
    log = sessions[session_id].get_episode_log()
    sla_emails = [e for e in log if e.get("sla_hours") is not None]
    breaches = [e for e in sla_emails if e.get("sla_hours",999)<=2 and e["agent_action"]["action"]=="archive"]
    return {"session_id":session_id,"emails_with_sla":len(sla_emails),"sla_breaches":len(breaches),
            "breach_details":[{"subject":e["subject"][:60],"sla_hours":e["sla_hours"],"action_taken":e["agent_action"]["action"]} for e in breaches],
            "compliance_rate":round(1-len(breaches)/max(1,len(sla_emails)),3)}

@app.post("/leaderboard")
async def submit_leaderboard(entry: LeaderboardEntry):
    record = {"rank":0,"agent_name":entry.agent_name,"score":round(max(0.001,min(0.999,entry.score)),4),
              "task_id":entry.task_id,"model":entry.model,"notes":entry.notes,"submitted_at":utcnow()}
    _leaderboard.append(record)
    _leaderboard.sort(key=lambda x: x["score"], reverse=True)
    for i,r in enumerate(_leaderboard): r["rank"]=i+1
    return {"message":"Submitted!","rank":record["rank"],"entry":record}

@app.get("/leaderboard")
async def get_leaderboard(task_id: Optional[str] = None, limit: int = 10):
    board = [r for r in _leaderboard if not task_id or r["task_id"]==task_id]
    return {"leaderboard":board[:limit],"total_entries":len(board),"filter":task_id or "all"}

@app.get("/tasks")
async def list_tasks():
    return {"tasks":[
        {"id":"task_easy_spam","difficulty":"easy","description":"Spam detection + basic priority","num_emails":5,"passing_score":0.60},
        {"id":"task_medium_triage","difficulty":"medium","description":"Full triage across mixed inbox","num_emails":10,"passing_score":0.55},
        {"id":"task_hard_ambiguous","difficulty":"hard","description":"Multilingual, legal, edge-case emails","num_emails":13,"passing_score":0.45},
    ]}

@app.get("/validate")
async def validate_environment():
    errors = []
    try:
        env = EmailTriageEnv(task_id="validate", num_emails=3, seed=1)
        obs = env.reset()
        assert obs.email_id != "DONE"
        action = TriageAction(email_id=obs.email_id, priority=Priority.MEDIUM, category=Category.OTHER, action="archive")
        obs2, reward, done, info = env.step(action)
        assert isinstance(reward,float) and -1.0<=reward<=1.0
        assert "ground_truth" in info
        state = env.state()
        assert hasattr(state,"sla_breaches")
        assert 0.0<=env.get_score()<=1.0
    except Exception as e: errors.append(str(e))
    return {"valid":len(errors)==0,"errors":errors,
            "checks_passed":["reset","step","reward_range","state","score","sla_tracking"] if not errors else [],
            "timestamp":utcnow()}

def _run_grader_score(task_id, num_emails, seed):
    env = EmailTriageEnv(task_id=task_id, num_emails=num_emails, seed=seed)
    obs = env.reset()
    while obs.email_id != "DONE":
        action = TriageAction(email_id=obs.email_id, priority=Priority.MEDIUM, category=Category.OTHER, action="archive")
        obs, _, done, _ = env.step(action)
        if done: break
    return max(0.01, min(0.99, env.get_score()))

@app.get("/grade/task_easy")
@app.post("/grade/task_easy")
async def grade_easy(): return {"score":_run_grader_score("task_easy_spam",5,42),"task_id":"task_easy_spam"}

@app.get("/grade/task_medium")
@app.post("/grade/task_medium")
async def grade_medium(): return {"score":_run_grader_score("task_medium_triage",10,99),"task_id":"task_medium_triage"}

@app.get("/grade/task_hard")
@app.post("/grade/task_hard")
async def grade_hard(): return {"score":_run_grader_score("task_hard_ambiguous",13,777),"task_id":"task_hard_ambiguous"}

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir): app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""): return FileResponse(os.path.join(_static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT",7860)), reload=False)
