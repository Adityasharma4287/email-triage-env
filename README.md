---
title: Email Triage App
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: true
---

# 📧 Email Triage — OpenEnv RL Environment

> **OpenEnv Hackathon Submission** — Meta × Scaler × Hugging Face
> A production-ready RL environment that trains AI agents to manage real-world email inboxes.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-v1.0-blue)](https://github.com/Adityasharma4287/email-triage-env)
[![HF Space](https://img.shields.io/badge/🤗-Live%20Demo-yellow)](https://huggingface.co/spaces/Adityasharma4287/email-triage-app)
[![Docker](https://img.shields.io/badge/Docker-ready-brightgreen)](./Dockerfile)
[![Fine-tuned Model](https://img.shields.io/badge/🦙-Llama%20GRPO-orange)](https://huggingface.co/Adityasharma4287/email-triage-llama-rl)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🏆 Achieved Scores

| Task | Difficulty | Passing Threshold | Our Score | Status |
|---|---|---|---|---|
| `task_easy_spam` | 🟢 Easy | 0.60 | **0.660** | ✅ Pass |
| `task_medium_triage` | 🟡 Medium | 0.55 | **0.606** | ✅ Pass |
| `task_hard_ambiguous` | 🔴 Hard | 0.45 | **0.619** | ✅ Pass |

> All 3 tasks passed. Scores strictly in `(0.0, 1.0)` as per OpenEnv spec.

---

## 🎯 What Is This?

Email triage is one of the most universal real-world tasks — knowledge workers spend **28% of their workweek on email**. This OpenEnv-compliant environment trains AI agents to:

- **Classify** emails: spam, urgent, billing, technical, sales, internal, etc.
- **Prioritize** intelligently: `urgent → high → medium → low → spam`
- **Route correctly**: reply, escalate, archive, forward, or delete
- Handle **ambiguous edge cases**: security disclosures, angry CFO emails, phishing that looks real, multi-language emails

Unlike toy environments, this requires true natural language understanding and nuanced judgment — not binary right/wrong.

---

## 🤖 Fine-tuned Model

We fine-tuned **Llama 3.1 8B** using **GRPO (Group Relative Policy Optimization)**:

- **Base**: `meta-llama/Llama-3.1-8B` (4-bit quantized)
- **Method**: GRPO Reinforcement Learning on email triage tasks
- **Published**: [Adityasharma4287/email-triage-llama-rl](https://huggingface.co/Adityasharma4287/email-triage-llama-rl)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("Adityasharma4287/email-triage-llama-rl")
tokenizer = AutoTokenizer.from_pretrained("Adityasharma4287/email-triage-llama-rl")
```

---

## 🔬 Action & Observation Space

### Observation — `EmailObservation`

| Field | Type | Description |
|---|---|---|
| `email_id` | str | Unique email identifier |
| `subject` | str | Email subject line |
| `sender` | str | Sender's email address |
| `body` | str | Full email body |
| `timestamp` | str | ISO 8601 received timestamp |
| `has_attachment` | bool | Whether email has attachment |
| `thread_length` | int | Number of messages in thread |
| `inbox_count` | int | Emails remaining to process |
| `processed_count` | int | Emails already processed |
| `current_score` | float | Running score strictly in `(0, 1)` |
| `step_number` | int | Current step in episode |

### Action — `TriageAction`

| Field | Type | Options |
|---|---|---|
| `priority` | enum | `urgent` · `high` · `medium` · `low` · `spam` |
| `category` | enum | `customer_support` · `billing` · `technical` · `sales` · `internal` · `spam` · `other` |
| `action` | enum | `reply` · `archive` · `escalate` · `delete` · `forward` |
| `reply_text` | str? | Reply content (optional, bonus if len > 50) |
| `forward_to` | str? | Recipient email if forwarding |
| `notes` | str? | Agent's reasoning notes |

---

## 🏆 Reward Function

Rewards are computed **per step** (not end-of-episode) for continuous learning signal:

```
reward = priority_score  × 0.40
       + category_score  × 0.30
       + action_score    × 0.30
       + reply_bonus     × 0.05   (if reply_text provided and len > 50)
       - urgent_penalty  × 0.30   (if urgent email is archived)
```

**Priority scoring** (graded scale):

| Difference | Score |
|---|---|
| Exact match | +1.0 |
| Off by 1 | +0.3 |
| Off by 2 | -0.2 |
| Wildly wrong | -1.0 |

**Action scoring:**
- Exact match → `+1.0`
- Reasonable alternative (e.g. `escalate` instead of `forward`) → `+0.4`
- Dangerous (e.g. `delete` on urgent email) → `-1.0`

Final score is clamped strictly to `(0.001, 0.999)` — 0.0 and 1.0 are never returned.

---

## 📋 Tasks

| Task ID | Difficulty | Emails | Seed | Description | Passing Threshold |
|---|---|---|---|---|---|
| `task_easy_spam` | 🟢 Easy | 5 | 42 | Spam detection + basic priority | 0.60 |
| `task_medium_triage` | 🟡 Medium | 10 | 99 | Full triage across all categories | 0.55 |
| `task_hard_ambiguous` | 🔴 Hard | 13 | 777 | Security disclosures, long threads, edge cases | 0.45 |

**Hard task includes edge cases like:**
- Phishing disguised as PayPal security alerts
- GDPR legal requests with 30-day deadlines
- Angry CFO disputing a double charge (`$4,200`)
- Security researcher reporting SQL injection (no money demanded)
- Multi-language billing complaints (Spanish)

---

## 🚀 Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/Adityasharma4287/email-triage-env
cd email-triage-env

docker build -t email-triage-env .
docker run -p 7860:7860 email-triage-env

open http://localhost:7860/app    # React dashboard
open http://localhost:7860/docs   # Swagger API docs
```

### Local Development

```bash
pip install -r requirements.txt
uvicorn app:app --reload --port 7860

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Run Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="hf_..."
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

---

## 🐍 Python Usage

```python
from env.email_triage_env import EmailTriageEnv, TriageAction, Priority, Category

env = EmailTriageEnv(task_id="task_medium_triage", num_emails=10, seed=99)
obs = env.reset()

while obs.email_id != "DONE":
    action = TriageAction(
        email_id=obs.email_id,
        priority=Priority.HIGH,
        category=Category.CUSTOMER_SUPPORT,
        action="escalate",
        notes="Angry customer, urgent billing issue"
    )
    obs, reward, done, info = env.step(action)
    print(f"Reward: {reward:.4f} | Score: {obs.current_score:.4f}")
    if done:
        break

print(f"Final Score: {env.get_score()}")
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Submit a triage action |
| `GET` | `/state/{session_id}` | Get episode state |
| `GET` | `/score/{session_id}` | Get normalized score |
| `GET` | `/validate` | OpenEnv spec self-test |
| `GET` | `/tasks` | List all available tasks |
| `GET` | `/log/{session_id}` | Full decision log |
| `GET` | `/app` | React dashboard UI |
| `GET` | `/docs` | Swagger API docs |

---

## ✅ OpenEnv Spec Compliance

```bash
curl http://localhost:7860/validate
```

```json
{
  "valid": true,
  "errors": [],
  "checks_passed": [
    "reset() returns EmailObservation",
    "step() returns (obs, reward, done, info)",
    "reward in [-1.0, 1.0]",
    "state() returns EnvironmentState",
    "score in (0.0, 1.0) strictly"
  ]
}
```

---

## 📁 Project Structure

```
email-triage-env/
├── app.py                  # FastAPI server (OpenEnv HTTP interface)
├── inference.py            # Baseline inference script
├── smart_agent.py          # Fine-tuned Llama agent
├── openenv.yaml            # OpenEnv metadata spec
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Local dev compose
├── baseline_scores.json    # GPT-4o-mini baseline reference
├── env/
│   └── email_triage_env.py # Core RL environment + 25 email templates
├── graders/
│   └── graders.py          # Easy / Medium / Hard graders
└── frontend/
    └── src/App.jsx         # Animated React dashboard
```

---

## 📦 Dependencies

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
openai==1.57.0
python-multipart==0.0.18
httpx==0.28.1
requests
```

---

## 🔗 Links

| Resource | Link |
|---|---|
| GitHub | [email-triage-env](https://github.com/Adityasharma4287/email-triage-env) |
| HF Space | [email-triage-app](https://huggingface.co/spaces/Adityasharma4287/email-triage-app) |
| Fine-tuned Model | [email-triage-llama-rl](https://huggingface.co/Adityasharma4287/email-triage-llama-rl) |

```bash
git remote add space https://huggingface.co/spaces/Adityasharma4287/email-triage-env
git push space main
```

---

## 🤝 Contributing

1. Fork the repo
2. Create your branch: `git checkout -b feature/YourFeature`
3. Commit: `git commit -m 'Add YourFeature'`
4. Push: `git push origin feature/YourFeature`
5. Open a Pull Request

---

*Built for the OpenEnv Hackathon — Meta × Hugging Face × Scaler School of Technology*
*Developer: Aditya Sharma — Scaler School of Technology*

> ⭐ If this helped you, please star the repo — it helps others discover it!
