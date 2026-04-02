"""
Email Triage OpenEnv - FastAPI Server
Exposes the environment via HTTP API for agent interaction and the React dashboard.
"""
import os
import sys
import json
import time
import uuid
from typing import Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from env.email_triage_env import EmailTriageEnv, TriageAction, Priority, Category, EmailObservation

app = FastAPI(
    title="Email Triage OpenEnv",
    description="OpenEnv-compliant email triage environment for AI agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory session store ────────────────────────────────────────────────

sessions: dict[str, EmailTriageEnv] = {}
session_metadata: dict[str, dict] = {}


# ─── Request / Response Models ───────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "task_medium_triage"
    num_emails: int = 10
    seed: int = 42


class StepRequest(BaseModel):
    session_id: str
    priority: str
    category: str
    action: str
    reply_text: Optional[str] = None
    forward_to: Optional[str] = None
    notes: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    observation: dict
    task_id: str
    started_at: str


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "email-triage-openenv",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/reset", "/step", "/state", "/score", "/validate", "/health"],
        "tasks": ["task_easy_spam", "task_medium_triage", "task_hard_ambiguous"],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "sessions": len(sessions)}


@app.post("/reset")
async def reset_environment(req: ResetRequest):
    """Start a new episode. Returns session_id and first email observation."""
    session_id = str(uuid.uuid4())[:8]
    env = EmailTriageEnv(task_id=req.task_id, num_emails=req.num_emails, seed=req.seed)
    obs = env.reset()
    sessions[session_id] = env
    session_metadata[session_id] = {
        "task_id": req.task_id,
        "started_at": datetime.utcnow().isoformat(),
        "steps": 0,
    }
    return {
        "session_id": session_id,
        "observation": obs.dict(),
        "task_id": req.task_id,
        "started_at": session_metadata[session_id]["started_at"],
    }


@app.post("/step")
async def step_environment(req: StepRequest):
    """Submit a triage action for the current email."""
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{req.session_id}' not found. Call /reset first.")

    env = sessions[req.session_id]
    state = env.state()

    if state.done:
        raise HTTPException(status_code=400, detail="Episode is done. Call /reset to start a new one.")

    # Validate action
    valid_actions = {"reply", "archive", "escalate", "delete", "forward"}
    if req.action not in valid_actions:
        raise HTTPException(status_code=422, detail=f"Invalid action '{req.action}'. Must be one of: {valid_actions}")

    try:
        priority = Priority(req.priority)
        category = Category(req.category)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    current_obs = env._make_observation()
    action = TriageAction(
        email_id=current_obs.email_id,
        priority=priority,
        category=category,
        action=req.action,
        reply_text=req.reply_text,
        forward_to=req.forward_to,
        notes=req.notes,
    )

    obs, reward, done, info = env.step(action)
    session_metadata[req.session_id]["steps"] += 1

    return {
        "observation": obs.dict(),
        "reward": reward,
        "done": done,
        "info": info,
        "session_id": req.session_id,
    }


@app.get("/state/{session_id}")
async def get_state(session_id: str):
    """Get the full current state of an environment session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    state = env.state()
    return {
        **state.dict(),
        "score": env.get_score(),
        "metadata": session_metadata.get(session_id, {}),
    }


@app.get("/score/{session_id}")
async def get_score(session_id: str):
    """Get the current normalized score for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    return {
        "session_id": session_id,
        "score": env.get_score(),
        "cumulative_reward": env._cumulative_reward,
        "done": env._done,
        "steps": env._step_count,
    }


@app.get("/log/{session_id}")
async def get_episode_log(session_id: str):
    """Get the full decision log for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    return {"session_id": session_id, "log": env.get_episode_log()}


@app.get("/validate")
async def validate_environment():
    """
    OpenEnv validation endpoint.
    Runs a quick self-test to verify the environment is spec-compliant.
    """
    errors = []
    try:
        env = EmailTriageEnv(task_id="validate", num_emails=3, seed=1)

        # Test reset()
        obs = env.reset()
        assert obs.email_id != "DONE", "reset() must return a valid observation"
        assert isinstance(obs.inbox_count, int), "inbox_count must be int"

        # Test step()
        action = TriageAction(
            email_id=obs.email_id,
            priority=Priority.MEDIUM,
            category=Category.OTHER,
            action="archive",
        )
        obs2, reward, done, info = env.step(action)
        assert isinstance(reward, float), "reward must be float"
        assert -1.0 <= reward <= 1.0, f"reward out of range: {reward}"
        assert isinstance(done, bool), "done must be bool"
        assert "ground_truth" in info, "info must contain ground_truth"

        # Test state()
        state = env.state()
        assert hasattr(state, "step_count"), "state() must have step_count"
        assert hasattr(state, "cumulative_reward"), "state() must have cumulative_reward"

        # Test score()
        score = env.get_score()
        assert 0.0 <= score <= 1.0, f"score out of range: {score}"

    except Exception as e:
        errors.append(str(e))

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "checks_passed": [
            "reset() returns EmailObservation",
            "step() returns (obs, reward, done, info)",
            "reward in [-1.0, 1.0]",
            "state() returns EnvironmentState",
            "score in [0.0, 1.0]",
        ] if not errors else [],
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/tasks")
async def list_tasks():
    """List all available tasks with descriptions and difficulty."""
    return {
        "tasks": [
            {
                "id": "task_easy_spam",
                "difficulty": "easy",
                "description": "Detect spam and assign basic priority levels",
                "num_emails": 5,
                "passing_score": 0.60,
                "expected_baseline_score": 0.45,
            },
            {
                "id": "task_medium_triage",
                "difficulty": "medium",
                "description": "Full triage: priority + category + action across mixed inbox",
                "num_emails": 10,
                "passing_score": 0.55,
                "expected_baseline_score": 0.40,
            },
            {
                "id": "task_hard_ambiguous",
                "difficulty": "hard",
                "description": "Handle ambiguous, multi-threaded, and edge-case emails",
                "num_emails": 13,
                "passing_score": 0.45,
                "expected_baseline_score": 0.30,
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)


# ─── Serve React SPA (must be LAST) ─────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    # Serve assets (JS, CSS, images)
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        return FileResponse(os.path.join(_static_dir, "index.html"))
