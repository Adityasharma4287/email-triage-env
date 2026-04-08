"""
Baseline inference script — Email Triage OpenEnv
Uses the OpenAI API client via API_BASE_URL / MODEL_NAME / HF_TOKEN env vars.
Produces reproducible baseline scores on all 3 tasks.

Usage:
  export API_BASE_URL="https://api.openai.com/v1"
  export MODEL_NAME="gpt-4o-mini"
  export HF_TOKEN="sk-..."
  export ENV_BASE_URL="http://localhost:7860"   # or your HF Space URL
  python inference.py
"""

import os, json, time, sys
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL  = os.environ.get("API_BASE_URL",  "https://api.openai.com/v1")
MODEL_NAME    = os.environ.get("MODEL_NAME",    "gpt-4o-mini")
HF_TOKEN      = os.environ.get("HF_TOKEN",      "")
ENV_BASE_URL  = os.environ.get("ENV_BASE_URL",  "http://localhost:7860")

client = OpenAI(api_key=HF_TOKEN or "dummy", base_url=API_BASE_URL)

TASKS = [
    {"id": "task_easy_spam",       "num_emails": 5,  "seed": 42},
    {"id": "task_medium_triage",   "num_emails": 10, "seed": 42},
    {"id": "task_hard_ambiguous",  "num_emails": 13, "seed": 42},
]

SYSTEM_PROMPT = """You are an expert email triage assistant.

For each email, respond ONLY with a valid JSON object (no markdown, no preamble):
{
  "priority": "urgent" | "high" | "medium" | "low" | "spam",
  "category": "customer_support" | "billing" | "technical" | "sales" | "internal" | "spam" | "other",
  "action": "reply" | "archive" | "escalate" | "delete" | "forward",
  "reply_text": "string or null",
  "notes": "one-line reasoning"
}

Priority guide: urgent=drop everything, high=today, medium=this week, low=someday, spam=junk.
Action guide: reply=send response, escalate=flag to manager, forward=route to team, archive=done, delete=trash."""


def api(method, path, body=None):
    url = f"{ENV_BASE_URL}{path}"
    r = requests.request(method, url, json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def triage_email(obs: dict) -> dict:
    prompt = (
        f"Subject: {obs['subject']}\n"
        f"From: {obs['sender']}\n"
        f"Has attachment: {obs.get('has_attachment', False)}\n"
        f"Thread length: {obs.get('thread_length', 1)}\n\n"
        f"{obs['body']}"
    )
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Triage this email:\n\n{prompt}"},
        ],
        max_tokens=300,
        temperature=0.0,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
    return json.loads(raw.strip())


def run_task(task: dict) -> float:
    print(f"\n{'='*55}")
    print(f"[START]")
    print(f"  TASK: {task['id']}  ({task['num_emails']} emails)")
    print(f"{'='*55}")

    resp = api("POST", "/reset", task)
    session_id = resp["session_id"]
    obs = resp["observation"]

    total_reward = 0.0
    steps = 0

    while obs.get("email_id") != "DONE":
        subj = obs.get("subject", "")[:55]
        print(f"\n[STEP {steps+1}] {subj}...")

        try:
            decision = triage_email(obs)
        except Exception as e:
            print(f"     ⚠ LLM error: {e} — using fallback")
            decision = {"priority": "medium", "category": "other",
                        "action": "archive", "reply_text": None, "notes": "fallback"}

        print(f"     → priority={decision.get('priority')}  "
              f"category={decision.get('category')}  "
              f"action={decision.get('action')}")

        try:
            result = api("POST", "/step", {
                "session_id": session_id,
                "priority":   decision.get("priority",  "medium"),
                "category":   decision.get("category",  "other"),
                "action":     decision.get("action",    "archive"),
                "reply_text": decision.get("reply_text"),
                "notes":      decision.get("notes", ""),
            })
        except Exception as e:
            print(f"     ✗ Step error: {e}")
            break

        reward = result.get("reward", 0.0)
        total_reward += reward
        steps += 1
        gt = result.get("info", {}).get("ground_truth", {})
        print(f"     reward={reward:+.3f}  gt={gt}")

        if result.get("done"):
            break
        obs = result["observation"]

    score = total_reward / steps if steps > 0 else -0.999
    # Normalize from [-1,1] to (0,1) strictly — 0.0 and 1.0 are not allowed
    raw = (score + 1.0) / 2.0
    normalized = max(0.001, min(0.999, round(raw, 4)))
    print(f"\n[END]")
    print(f"  ✓ Done — {steps} emails | raw_score={score:.4f} | normalized={normalized:.4f}")
    return normalized


def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║      Email Triage OpenEnv — Baseline Inference       ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"  Model  : {MODEL_NAME}")
    print(f"  API    : {API_BASE_URL}")
    print(f"  Env    : {ENV_BASE_URL}")

    # Health check
    try:
        h = api("GET", "/health")
        print(f"\n  ✅ Environment healthy: {h}\n")
    except Exception as e:
        print(f"\n  ❌ Cannot reach environment at {ENV_BASE_URL}")
        print(f"     {e}")
        print("  → Start it with: docker run -p 7860:7860 email-triage-env")
        sys.exit(1)

    scores = {}
    t0 = time.time()

    for task in TASKS:
        try:
            scores[task["id"]] = run_task(task)
        except Exception as e:
            print(f"\n  ❌ Task {task['id']} failed: {e}")
            scores[task["id"]] = 0.001  # strictly > 0.0
        time.sleep(0.5)

    elapsed = time.time() - t0
    avg_raw = sum(scores.values()) / len(scores)
    avg = max(0.001, min(0.999, round(avg_raw, 4)))

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║                  BASELINE SCORES                    ║")
    print("╠══════════════════════════════════════════════════════╣")
    for tid, s in scores.items():
        bar  = "█" * int(s * 24) + "░" * (24 - int(s * 24))
        print(f"║  {tid.split('_')[1]:<8} │ {bar} │ {s:.4f} ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  AVERAGE  │ {avg:.4f}  ({elapsed:.1f}s){'':>29}║")
    print("╚══════════════════════════════════════════════════════╝")

    out = {"model": MODEL_NAME, "scores": scores, "average": avg, "elapsed_seconds": round(elapsed, 2)}
    with open("baseline_scores.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n  📄 Results saved → baseline_scores.json")


if __name__ == "__main__":
    main()
