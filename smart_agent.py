"""
Smart Agent v3 — Email Triage OpenEnv
=======================================
v2 ke features:
  1. Memory          — Same sender history yaad rakhta hai
  2. Chain-of-Thought — Sochta hai phir decide karta hai
  3. Confidence Scoring — Uncertain pe auto-escalate

v3 mein 3 NAYE features:
  4. ReflectionEngine      — Galtiyon se seekhta hai: bura reward aaya toh
                             LLM se poochha 'kya galat tha?' aur lesson store karta hai.
                             Agli baar woh lesson prompt mein inject hota hai.

  5. AdaptivePromptBuilder — Task difficulty ke hisaab se alag system prompt.
                             Easy: short rules. Hard: detailed warnings + tricky examples.

  6. MultiPassDecision     — Hard emails pe 2 baar sochta hai alag temperatures pe.
                             Agree → confident result. Disagree → auto-escalate (safer).

Usage:
  export API_BASE_URL="https://api.openai.com/v1"
  export MODEL_NAME="gpt-4o-mini"
  export API_KEY="sk-..."
  export ENV_BASE_URL="http://localhost:7860"
  python smart_agent.py
"""

import os, json, time, sys
from collections import defaultdict
import requests
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "gpt-4o-mini")
API_KEY      = os.environ.get("API_KEY", os.environ.get("HF_TOKEN", "dummy"))
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

TASKS = [
    {"id": "task_easy_spam",      "num_emails": 5,  "seed": 42},
    {"id": "task_medium_triage",  "num_emails": 10, "seed": 42},
    {"id": "task_hard_ambiguous", "num_emails": 13, "seed": 42},
]


# =============================================================================
# FEATURE 1 (v2): AgentMemory
# =============================================================================
class AgentMemory:
    """Past decisions yaad rakhta hai. Same sender dobara aaye toh context milta hai."""

    def __init__(self):
        self.sender_history: dict = defaultdict(list)
        self.pattern_stats:  dict = defaultdict(lambda: {"correct": 0, "total": 0})
        self.session_log:    list = []

    def remember(self, email: dict, decision: dict, reward: float) -> None:
        sender = email.get("sender", "unknown")
        entry  = {
            "subject":   email.get("subject", ""),
            "decision":  decision,
            "reward":    reward,
            "timestamp": time.time(),
        }
        self.sender_history[sender].append(entry)
        self.session_log.append({**entry, "sender": sender})
        key = f"{decision.get('priority')}_{decision.get('action')}"
        self.pattern_stats[key]["total"] += 1
        if reward > 0.6:
            self.pattern_stats[key]["correct"] += 1

    def recall_sender(self, sender: str) -> str:
        history = self.sender_history.get(sender, [])
        if not history:
            return ""
        last = history[-1]
        avg_r = sum(h["reward"] for h in history) / len(history)
        return (
            f"[MEMORY] '{sender}' pehle {len(history)}x aaya. "
            f"Last: priority={last['decision'].get('priority')}, "
            f"action={last['decision'].get('action')}, reward={last['reward']:.2f}. "
            f"Avg: {avg_r:.2f}."
        )

    def best_patterns(self) -> str:
        good = []
        for key, s in self.pattern_stats.items():
            if s["total"] >= 2 and s["correct"] / s["total"] >= 0.7:
                good.append(f"{key}({s['correct']/s['total']:.0%})")
        return f"[PATTERNS] {', '.join(good[:4])}" if good else ""

    def summary(self) -> dict:
        total = len(self.session_log)
        if not total:
            return {"total_decisions": 0}
        return {
            "total_decisions": total,
            "unique_senders":  len(self.sender_history),
            "avg_reward":      round(sum(e["reward"] for e in self.session_log) / total, 4),
            "top_patterns":    self.best_patterns(),
        }


# =============================================================================
# FEATURE 4 (v3 NEW): ReflectionEngine
# =============================================================================
class ReflectionEngine:
    """
    Agent apni galtiyon se seekhta hai.

    Flow:
      reward < 0.4  →  LLM se poochho 'kya galat tha aur lesson kya hai'
                    →  Lesson store karo (max 5, sliding window)
                    →  Agli baar prompt mein inject karo

    Yeh ek meta-learning loop hai — agent sirf data nahi,
    apni reasoning bhi improve karta hai over time.
    """

    def __init__(self, max_lessons: int = 5):
        self.lessons:     list = []
        self.max_lessons: int  = max_lessons
        self.reflections: int  = 0

    def reflect(self, obs: dict, decision: dict, reward: float, ground_truth: dict):
        """Agar reward bura tha, LLM se reflection lo aur lesson store karo."""
        if reward >= 0.5:
            return None

        self.reflections += 1
        prompt = (
            f"You made a wrong email triage decision. Analyze briefly.\n\n"
            f"Subject: {obs.get('subject','')}\n"
            f"Sender:  {obs.get('sender','')}\n"
            f"Body:    {obs.get('body','')[:200]}\n\n"
            f"Your decision: priority={decision.get('priority')}, "
            f"category={decision.get('category')}, action={decision.get('action')}\n"
            f"Correct answer: priority={ground_truth.get('priority')}, "
            f"category={ground_truth.get('category')}, action={ground_truth.get('action')}\n\n"
            f"Respond ONLY with JSON:\n"
            f'{{ "mistake": "one sentence", "lesson": "one sentence", "pattern": "trigger word" }}'
        )
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.0,
            )
            raw = resp.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1].lstrip("json").strip()
            ref = json.loads(raw)
            lesson = (
                f"[LESSON #{self.reflections}] "
                f"Pattern='{ref.get('pattern','')}': {ref.get('lesson','')}"
            )
            self.lessons.append(lesson)
            if len(self.lessons) > self.max_lessons:
                self.lessons.pop(0)
            print(f"  🔍 Mistake : {ref.get('mistake','')}")
            print(f"  📝 Lesson  : {ref.get('lesson','')}")
            return lesson
        except Exception as e:
            print(f"  ⚠ Reflection failed: {e}")
            return None

    def get_context(self) -> str:
        if not self.lessons:
            return ""
        return "\n[PAST MISTAKES — avoid these]\n" + "\n".join(self.lessons)

    def summary(self) -> dict:
        return {
            "total_reflections": self.reflections,
            "lessons_stored":    len(self.lessons),
            "lessons":           self.lessons,
        }


# =============================================================================
# FEATURE 5 (v3 NEW): AdaptivePromptBuilder
# =============================================================================
_BASE = """You are an expert email triage assistant.
Respond ONLY with JSON (no markdown):
{
  "reasoning": "2-3 sentence analysis",
  "priority": "urgent|high|medium|low|spam",
  "category": "customer_support|billing|technical|sales|internal|spam|other",
  "action": "reply|archive|escalate|delete|forward",
  "reply_text": "string or null",
  "confidence": 0.0-1.0,
  "notes": "one line"
}
Priority: urgent=drop everything, high=today, medium=week, low=someday, spam=junk.
Action: escalate=manager, forward=team, reply=you respond, archive=done, delete=trash only for spam."""

_EASY_EXTRA = """
EASY TASK TIPS:
- Spam: suspicious domains (.xyz, free prize, caps lock) → priority=spam, action=delete.
- Urgent: production down OR payment declined with hard deadline.
- Low: newsletters, thank-you notes, internal FYI → archive."""

_MEDIUM_EXTRA = """
MEDIUM TASK TIPS:
- 'Following up' from real company domain → HIGH sales, action=reply or forward.
- Developer asking about API limits → MEDIUM technical, action=reply.
- Subscription cancellation from long-term customer → HIGH billing, action=reply (try to save them).
- Feature requests → MEDIUM customer_support, action=reply."""

_HARD_EXTRA = """
HARD TASK — EXTRA CAUTION REQUIRED:
- Legal/GDPR emails → HIGH or URGENT, always escalate.
- Security disclosure from unknown sender → URGENT technical, escalate immediately.
- Polite but urgent: look for 'CEO asking', 'end of week', 'legal team', deadlines.
- Multi-language emails: Spanish/French urgency signals = same as English.
- Phishing detection: check sender domain carefully — paypa1, amaz0n, .xyz = spam.
- CFO complaining about double-charge → URGENT billing, escalate.
- When torn between high/urgent → choose URGENT. Missing urgent costs more than false alarm.
- Partnership pitch from startup CEO → HIGH sales, forward to sales team."""


class AdaptivePromptBuilder:
    """
    Har task ki difficulty ke hisaab se alag system prompt banata hai.
    Easy → short (save tokens). Hard → detailed rules + tricky examples.
    """

    def __init__(self):
        self.current_task_id = "task_medium_triage"

    def set_task(self, task_id: str) -> None:
        self.current_task_id = task_id
        label = "EASY" if "easy" in task_id else "HARD" if "hard" in task_id else "MEDIUM"
        print(f"  [AdaptivePrompt] Task difficulty set to: {label}")

    def build_system_prompt(self, reflection_context: str = "") -> str:
        if "easy" in self.current_task_id:
            addon = _EASY_EXTRA
        elif "hard" in self.current_task_id:
            addon = _HARD_EXTRA
        else:
            addon = _MEDIUM_EXTRA
        prompt = _BASE + addon
        if reflection_context:
            prompt += f"\n{reflection_context}"
        return prompt

    def build_user_prompt(self, obs: dict, memory_context: str) -> str:
        lines = [
            f"Subject: {obs['subject']}",
            f"From:    {obs['sender']}",
            f"Attach:  {obs.get('has_attachment', False)}",
            f"Thread:  {obs.get('thread_length', 1)} messages",
            f"Inbox remaining: {obs.get('inbox_count', '?')}",
        ]
        if memory_context:
            lines.append(memory_context)
        lines += ["", obs["body"]]
        return "Triage this email:\n\n" + "\n".join(lines)


# =============================================================================
# FEATURE 6 (v3 NEW): MultiPassDecision
# =============================================================================
def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)


def multipass_decision(system_prompt: str, user_prompt: str, passes: int = 2) -> dict:
    """
    Email pe multiple baar sochta hai (alag temperatures).
    - Agree on priority+action → confident decision (confidence +0.05 bonus)
    - Disagree → auto-escalate with lower confidence (safer for hard emails)
    """
    temperatures = [0.0, 0.4]
    responses    = []

    for i, temp in enumerate(temperatures[:passes]):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=400,
                temperature=temp,
            )
            dec = _parse_json(resp.choices[0].message.content)
            dec["_pass"] = i + 1
            responses.append(dec)
        except Exception as e:
            print(f"  ⚠ Pass {i+1} error: {e}")

    if not responses:
        return {"priority": "medium", "category": "other", "action": "escalate",
                "confidence": 0.3, "notes": "all passes failed", "_multipass": "failed"}
    if len(responses) == 1:
        responses[0]["_multipass"] = "single"
        return responses[0]

    r1, r2 = responses[0], responses[1]
    agree  = (r1.get("priority") == r2.get("priority") and
              r1.get("action")   == r2.get("action"))

    if agree:
        best = max(responses, key=lambda x: x.get("confidence", 0))
        best["_multipass"] = "agree"
        best["confidence"] = min(0.999, best.get("confidence", 0.8) + 0.05)
        return best
    else:
        r1["action"]     = "escalate"
        r1["confidence"] = 0.55
        r1["notes"]      = (
            f"[MULTIPASS DISAGREE] P1={r1.get('priority')}/{responses[0].get('action')} "
            f"vs P2={r2.get('priority')}/{r2.get('action')} → auto-escalated."
        )
        r1["_multipass"] = "disagree"
        return r1


# =============================================================================
# FEATURE 3 (v2): Confidence-based Auto-Escalation
# =============================================================================
def adjust_for_confidence(decision: dict) -> dict:
    conf = decision.get("confidence", 1.0)
    if conf < 0.65 and decision.get("action") not in ("delete", "escalate"):
        orig = decision["action"]
        decision["action"] = "escalate"
        decision["notes"]  = (
            f"[AUTO-ESCALATED conf={conf:.2f}] was='{orig}'. "
            + decision.get("notes", "")
        )
    return decision


# =============================================================================
# Core triage — all 6 features wired together
# =============================================================================
def triage_email_v3(
    obs:            dict,
    memory:         AgentMemory,
    reflection:     ReflectionEngine,
    prompt_builder: AdaptivePromptBuilder,
) -> dict:
    # Gather all context
    mem_ctx = "\n".join(filter(None, [
        memory.recall_sender(obs.get("sender", "")),
        memory.best_patterns(),
    ]))
    system_prompt = prompt_builder.build_system_prompt(reflection.get_context())
    user_prompt   = prompt_builder.build_user_prompt(obs, mem_ctx)

    # Hard task → 2 passes; easy/medium → 1 pass (save API calls)
    if "hard" in prompt_builder.current_task_id:
        decision = multipass_decision(system_prompt, user_prompt, passes=2)
    else:
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=400,
                temperature=0.0,
            )
            decision = _parse_json(resp.choices[0].message.content)
            decision["_multipass"] = "single"
        except Exception as e:
            decision = {"priority": "medium", "category": "other",
                        "action": "escalate", "confidence": 0.4,
                        "notes": f"parse error: {e}", "_multipass": "error"}

    return adjust_for_confidence(decision)


# =============================================================================
# Helpers
# =============================================================================
def clamp_score(s: float) -> float:
    return max(0.001, min(0.999, round(s, 4)))


def api(method: str, path: str, body=None) -> dict:
    r = requests.request(method, f"{ENV_BASE_URL}{path}", json=body, timeout=30)
    r.raise_for_status()
    return r.json()


# =============================================================================
# Task runner
# =============================================================================
def run_task_v3(
    task:           dict,
    memory:         AgentMemory,
    reflection:     ReflectionEngine,
    prompt_builder: AdaptivePromptBuilder,
) -> float:
    print(f"\n{'='*65}")
    print(f"[v3] task={task['id']}  ({task['num_emails']} emails)")
    print(f"{'='*65}")

    prompt_builder.set_task(task["id"])

    resp       = api("POST", "/reset", task)
    session_id = resp["session_id"]
    obs        = resp["observation"]

    total_reward = 0.0
    steps        = 0

    while obs.get("email_id") != "DONE":
        print(f"\n[STEP {steps+1}] {obs.get('subject','')[:55]}...")

        try:
            decision = triage_email_v3(obs, memory, reflection, prompt_builder)
        except Exception as e:
            print(f"  ⚠ Error: {e} — fallback")
            decision = {"priority": "medium", "category": "other",
                        "action": "escalate", "confidence": 0.4,
                        "notes": "fallback", "_multipass": "fallback"}

        mp   = decision.get("_multipass", "?")
        conf = decision.get("confidence", 1.0)
        print(
            f"  → {decision.get('priority'):<8} | {decision.get('category'):<18} | "
            f"{decision.get('action'):<10} | conf={conf:.2f} | [{mp}]"
        )
        if decision.get("reasoning"):
            print(f"  💭 {decision['reasoning'][:95]}")

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
            print(f"  ✗ Step error: {e}")
            break

        raw_r  = result.get("reward", 0.0)
        reward = clamp_score((raw_r + 1.0) / 2.0)
        total_reward += reward
        steps        += 1

        gt    = result.get("info", {}).get("ground_truth", {})
        match = "✅" if (
            decision.get("priority") == gt.get("priority") and
            decision.get("action")   == gt.get("action")
        ) else "❌"
        print(f"  {match} reward={reward:.4f}  gt={gt}")

        # Update memory & reflect on mistakes
        memory.remember(obs, decision, reward)
        reflection.reflect(obs, decision, reward, gt)

        if result.get("done"):
            break
        obs = result["observation"]

    normalized = clamp_score(total_reward / steps) if steps else 0.001
    print(f"\n[END] {task['id']}  score={normalized:.4f}  steps={steps}")
    return normalized


# =============================================================================
# Main
# =============================================================================
def main() -> None:
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          Email Triage — SMART Agent v3.0                    ║")
    print("║  v2: Memory · Chain-of-Thought · Confidence Scoring         ║")
    print("║  v3: ReflectionEngine · AdaptivePrompt · MultiPassDecision  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"  Model : {MODEL_NAME}")
    print(f"  API   : {API_BASE_URL}")
    print(f"  Env   : {ENV_BASE_URL}")

    try:
        h = api("GET", "/health")
        print(f"\n  ✅ Healthy (sessions={h.get('sessions', 0)})\n")
    except Exception as e:
        print(f"\n  ❌ Cannot reach {ENV_BASE_URL}\n     {e}")
        sys.exit(1)

    memory         = AgentMemory()
    reflection     = ReflectionEngine(max_lessons=5)
    prompt_builder = AdaptivePromptBuilder()

    scores = {}
    t0     = time.time()

    for task in TASKS:
        try:
            scores[task["id"]] = run_task_v3(task, memory, reflection, prompt_builder)
        except Exception as e:
            print(f"\n  ❌ {task['id']} failed: {e}")
            scores[task["id"]] = 0.001
        time.sleep(0.5)

    elapsed = time.time() - t0
    avg     = clamp_score(sum(scores.values()) / len(scores))

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║                    v3 AGENT SCORES                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    for tid, s in scores.items():
        bar = "█" * int(s * 26) + "░" * (26 - int(s * 26))
        print(f"║  {tid.split('_')[1]:<8} │ {bar} │ {s:.4f} ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  AVERAGE  │ {avg:.4f}  ({elapsed:.1f}s){'':>33}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    mem_sum = memory.summary()
    ref_sum = reflection.summary()

    print(f"\n  📦 Memory   : {mem_sum['total_decisions']} decisions, "
          f"{mem_sum['unique_senders']} senders, avg_reward={mem_sum.get('avg_reward',0):.4f}")
    print(f"  🔍 Reflection: {ref_sum['total_reflections']} reflections, "
          f"{ref_sum['lessons_stored']} lessons stored")
    for i, l in enumerate(ref_sum["lessons"], 1):
        print(f"     [{i}] {l[:90]}")

    out = {
        "agent":   "smart_agent_v3",
        "model":   MODEL_NAME,
        "features": [
            "memory", "chain_of_thought", "confidence_scoring",
            "reflection_engine", "adaptive_prompt", "multipass_decision",
        ],
        "scores":           scores,
        "average":          avg,
        "elapsed_seconds":  round(elapsed, 2),
        "memory_summary":   mem_sum,
        "reflection_summary": ref_sum,
    }
    with open("smart_agent_scores.json", "w") as f:
        json.dump(out, f, indent=2)
    print("\n  📄 Saved → smart_agent_scores.json")


if __name__ == "__main__":
    main()
