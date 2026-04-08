# 📧 Email Triage OpenEnv

> **OpenEnv Hackathon Submission** — Meta × Scaler × Hugging Face  
> An OpenEnv-compliant RL environment simulating real-world email inbox management.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-v1.0-blue)](https://github.com/meta-pytorch/OpenEnv)
[![HF Space](https://img.shields.io/badge/🤗-HF%20Space-yellow)](https://huggingface.co/spaces/Adityasharma4287/email-triage-app)
[![Docker](https://img.shields.io/badge/Docker-ready-brightgreen)](./Dockerfile)

---

## 🎯 Environment Description & Motivation

Email triage is one of the most universal real-world tasks — knowledge workers spend 28% of their workweek on email. This environment trains AI agents to **classify, prioritize, and route emails** correctly, rewarding nuanced judgment and penalizing dangerous mistakes (e.g., archiving an urgent security incident).

Unlike toy environments, Email Triage requires:
- **Natural language understanding** — reading email context
- **Priority judgment** — distinguishing truly urgent from merely important
- **Routing intelligence** — knowing which team handles what
- **Partial credit sensitivity** — a reward function that grades nuance, not just binary right/wrong

---

## 🔬 Action & Observation Space

### Observation Space (`EmailObservation`)
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
| `current_score` | float | Running normalized score strictly in (0,1) |
| `step_number` | int | Current step in episode |

### Action Space (`TriageAction`)
| Field | Type | Options |
|---|---|---|
| `priority` | enum | `urgent` · `high` · `medium` · `low` · `spam` |
| `category` | enum | `customer_support` · `billing` · `technical` · `sales` · `internal` · `spam` · `other` |
| `action` | enum | `reply` · `archive` · `escalate` · `delete` · `forward` |
| `reply_text` | str? | Reply content (optional) |
| `forward_to` | str? | Forward recipient (optional) |
| `notes` | str? | Agent reasoning notes |

---

## 📋 Tasks

| Task ID | Difficulty | Emails | Seed | Description | Passing Threshold |
|---|---|---|---|---|---|
| `task_easy_spam` | 🟢 Easy | 5 | 42 | Spam detection + basic priority | 0.60 |
| `task_medium_triage` | 🟡 Medium | 10 | 99 | Full triage across all categories | 0.55 |
| `task_hard_ambiguous` | 🔴 Hard | 13 | 777 | Security disclosures, long threads, edge cases | 0.45 |

---

## 🏆 Reward Function

Rewards are computed **per step** (not end-of-episode), giving the agent signal throughout the trajectory:

```
reward = priority_score × 0.40
       + category_score × 0.30
       + action_score   × 0.30
       + reply_bonus    × 0.05   (if reply_text provided and len > 50)
       - urgent_penalty × 0.30   (if urgent email is archived/deleted)
```

- **Priority** scored on a graded scale (exact=1.0, off-by-one=0.3, off-by-two=-0.2, wildly wrong=-1.0)
- **Category** exact match=1.0, wrong=-0.5
- **Action** exact=1.0, reasonable alternative=0.4, dangerous=−1.0

Final score is **strictly normalized to (0.001, 0.999)** — 0.0 and 1.0 are never returned.

---

## 📊 Score Normalization

All scores are strictly between 0 and 1 (exclusive) in both `graders/graders.py` and `inference.py`:

```python
def normalize_score(score: float) -> float:
    if score <= 0:
        return 0.001
    elif score >= 1:
        return 0.999
    return round(score, 4)
```

In `inference.py`, the final task score is also clamped:
```python
normalized = (score + 1.0) / 2.0
normalized = max(0.001, min(0.999, round(normalized, 4)))
```

---

## 🚀 Setup & Usage

### Prerequisites
- Docker 24+
- Python 3.11+

### Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/Adityasharma4287/email-triage-env
cd email-triage-env

# Build & run
docker build -t email-triage-env .
docker run -p 7860:7860 email-triage-env

# Visit dashboard
open http://localhost:7860/app

# View API docs
open http://localhost:7860/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start backend
uvicorn app:app --reload --port 7860

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

### Run Baseline Inference

```bash
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="sk-..."
export ENV_BASE_URL="http://localhost:7860"

python inference.py
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe (must return 200) |
| `POST` | `/reset` | Start a new episode |
| `POST` | `/step` | Submit a triage action |
| `GET` | `/state/{session_id}` | Get episode state |
| `GET` | `/score/{session_id}` | Get normalized score |
| `GET` | `/validate` | OpenEnv spec self-test |
| `GET` | `/tasks` | List all available tasks |
| `GET` | `/log/{session_id}` | Get full decision log |
| `GET` | `/app` | React dashboard UI |
| `GET` | `/docs` | Swagger API documentation |

---

## 📁 Project Structure

```
email-triage-env/
├── app.py                  # FastAPI server (OpenEnv HTTP interface)
├── inference.py            # Baseline inference script (score strictly in (0,1))
├── openenv.yaml            # OpenEnv metadata spec
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Local development compose
├── README.md               # This file
├── env/
│   ├── __init__.py
│   └── email_triage_env.py # Core environment logic
├── graders/
│   ├── __init__.py
│   └── graders.py          # Task graders with normalize_score strictly (0,1)
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        └── App.jsx         # Animated React dashboard
```

---

## 📦 Dependencies (`requirements.txt`)

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

## 🧪 OpenEnv Spec Compliance

Run the built-in validation:
```bash
curl http://localhost:7860/validate
```

Expected output:
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

## 🤗 Deploying to Hugging Face Spaces

- **GitHub**: https://github.com/Adityasharma4287/email-triage-env
- **HF Space**: https://huggingface.co/spaces/Adityasharma4287/email-triage-app

```bash
git remote add space https://huggingface.co/spaces/Adityasharma4287/email-triage-env
git push space main
```

---

*Built for the OpenEnv Hackathon — Meta × Hugging Face × Scaler School of Technology*
