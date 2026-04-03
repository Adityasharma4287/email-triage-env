"""
Email Triage OpenEnv - FastAPI Server
OpenEnv-spec compliant: /reset /step /state /validate /health
"""
import os
import sys
import uuid
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))
from env.email_triage_env import (
    EmailTriageEnv,
    TriageAction,
    Priority,
    Category,
)

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

# ─── In-memory session store ─────────────────────────────────────────────────
sessions: dict[str, EmailTriageEnv] = {}
session_meta: dict[str, dict[str, object]] = {}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Request Models ───────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: str = "task_medium_triage"
    num_emails: int = 10
    seed: int = 42


class StepRequest(BaseModel):
    session_id: str
    priority: str = "medium"
    category: str = "other"
    action: str = "archive"
    reply_text: Optional[str] = None
    forward_to: Optional[str] = None
    notes: Optional[str] = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root() -> dict[str, object]:
    return {
        "name": "email-triage-openenv",
        "version": "1.0.0",
        "status": "running",
        "endpoints": ["/reset", "/step", "/state", "/score", "/validate", "/health"],
        "tasks": ["task_easy_spam", "task_medium_triage", "task_hard_ambiguous"],
    }


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "timestamp": utcnow(),
        "sessions": len(sessions),
    }


@app.post("/reset")
async def reset_environment(req: Optional[ResetRequest] = None) -> dict[str, object]:
    """
    Start a new episode. Body is optional — works with empty POST too.
    Returns session_id and first email observation.
    """
    if req is None:
        req = ResetRequest()

    session_id = str(uuid.uuid4())[:8]
    env = EmailTriageEnv(task_id=req.task_id, num_emails=req.num_emails, seed=req.seed)
    obs = env.reset()
    sessions[session_id] = env
    started_at = utcnow()
    session_meta[session_id] = {
        "task_id": req.task_id,
        "started_at": started_at,
        "steps": 0,
    }
    return {
        "session_id": session_id,
        "observation": obs.model_dump(),
        "task_id": req.task_id,
        "started_at": started_at,
    }


@app.post("/step")
async def step_environment(req: StepRequest) -> dict[str, object]:
    """Submit a triage action for the current email."""
    if req.session_id not in sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{req.session_id}' not found. Call /reset first.",
        )

    env = sessions[req.session_id]
    state = env.state()

    if state.done:
        raise HTTPException(
            status_code=400,
            detail="Episode is done. Call /reset to start a new one.",
        )

    valid_actions = {"reply", "archive", "escalate", "delete", "forward"}
    if req.action not in valid_actions:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{req.action}'. Must be one of: {sorted(valid_actions)}",
        )

    try:
        priority = Priority(req.priority)
        category = Category(req.category)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    current_obs = env.current_observation()
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
    steps = int(session_meta[req.session_id].get("steps", 0)) + 1
    session_meta[req.session_id]["steps"] = steps

    return {
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
        "session_id": req.session_id,
    }


@app.get("/state/{session_id}")
async def get_state(session_id: str) -> dict[str, object]:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    state = env.state()
    return {
        **state.model_dump(),
        "score": env.get_score(),
        "metadata": session_meta.get(session_id, {}),
    }


@app.get("/score/{session_id}")
async def get_score(session_id: str) -> dict[str, object]:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    return {
        "session_id": session_id,
        "score": env.get_score(),
        "cumulative_reward": env.cumulative_reward,
        "done": env.is_done,
        "steps": env.step_count,
    }


@app.get("/log/{session_id}")
async def get_episode_log(session_id: str) -> dict[str, object]:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    env = sessions[session_id]
    return {"session_id": session_id, "log": env.get_episode_log()}


@app.get("/validate")
async def validate_environment() -> dict[str, object]:
    """OpenEnv validation — runs a quick self-test."""
    errors: list[str] = []
    try:
        env = EmailTriageEnv(task_id="validate", num_emails=3, seed=1)

        obs = env.reset()
        assert obs.email_id != "DONE", "reset() must return a valid observation"
        assert isinstance(obs.inbox_count, int), "inbox_count must be int"

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

        state = env.state()
        assert hasattr(state, "step_count"), "state() must have step_count"
        assert hasattr(state, "cumulative_reward"), "state() must have cumulative_reward"

        score = env.get_score()
        assert 0.0 <= score <= 1.0, f"score out of range: {score}"

    except Exception as exc:
        errors.append(str(exc))

    checks_passed: list[str] = (
        [
            "reset() returns EmailObservation",
            "step() returns (obs, reward, done, info)",
            "reward in [-1.0, 1.0]",
            "state() returns EnvironmentState",
            "score in [0.0, 1.0]",
        ]
        if not errors
        else []
    )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "checks_passed": checks_passed,
        "timestamp": utcnow(),
    }


@app.get("/tasks")
async def list_tasks() -> dict[str, object]:
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


# ─── Serve React SPA — must be LAST ──────────────────────────────────────────
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = "") -> FileResponse:
        return FileResponse(os.path.join(_static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
