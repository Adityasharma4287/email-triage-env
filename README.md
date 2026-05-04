---
title: Email Triage App
emoji: 📧
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# 📧 Email Triage OpenEnv — Advanced v2.0

An OpenEnv-compliant email inbox triage environment for training and evaluating AI agents.

## 🆕 New in v2.0

| Feature | Description |
|---|---|
| ⏱ **SLA Tracking** | Each email has a deadline; missing urgent SLAs = extra penalty |
| 🧠 **Sentiment Scoring** | Angry customer detected → auto urgency boost in reward |
| 🏷️ **Custom Tags** | Agent can label emails: `VIP`, `churn-risk`, `legal-review`, `follow-up` |
| 💤 **Snooze Action** | New action type — snooze email for 1/4/8/24/48 hours |
| 📈 **Difficulty Ramp** | Session starts easy → gets harder automatically |
| ⚖️ **Legal / HR Categories** | Two new email categories added |
| 🌐 **Multilingual Emails** | Spanish, mixed-language test cases |
| 📊 **Sentiment Analytics** | `/sentiment/{id}` endpoint for anger/positivity analysis |
| 🚨 **SLA Report** | `/sla/{id}` endpoint for breach analysis |

## 🚀 Quick Start

```bash
git clone https://huggingface.co/spaces/Adityasharma4287/email-triage-app
cd email-triage-app
pip install -r requirements.txt
python app.py
# Open http://localhost:7860
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Start new episode |
| `/step` | POST | Submit triage decision |
| `/state/{id}` | GET | Full session state |
| `/score/{id}` | GET | Current score |
| `/analytics/{id}` | GET | Accuracy breakdown + mistakes |
| `/sentiment/{id}` | GET | 🆕 Sentiment analysis |
| `/sla/{id}` | GET | 🆕 SLA breach report |
| `/leaderboard` | GET/POST | Leaderboard |
| `/tasks` | GET | Available tasks |
| `/validate` | GET | Environment self-test |
| `/docs` | GET | Swagger UI |

## 🎯 Tasks

| Task | Difficulty | Emails | Passing Score |
|---|---|---|---|
| `task_easy_spam` | 🟢 Easy | 5 | 0.60 |
| `task_medium_triage` | 🟡 Medium | 10 | 0.55 |
| `task_hard_ambiguous` | 🔴 Hard | 13 | 0.45 |

## 🏷️ New: Custom Tags

```json
{
  "action": "escalate",
  "priority": "urgent",
  "category": "billing",
  "custom_tags": ["VIP", "churn-risk"]
}
```
Tags `VIP`, `legal-review`, `follow-up`, `churn-risk` on urgent/high emails give bonus reward.

## 💤 New: Snooze Action

```json
{
  "action": "snooze",
  "snooze_hours": 24
}
```

## 🤖 Running the Smart Agent

```bash
export API_KEY="your-openai-key"
export MODEL_NAME="gpt-4o-mini"
export ENV_BASE_URL="http://localhost:7860"
python smart_agent.py
```

## 📊 Reward Breakdown (v2)

- **Priority** (35%) — correct urgency level
- **Category** (25%) — correct department routing
- **Action** (30%) — correct action taken
- **Sentiment bonus** (5%) — angry customer handled correctly
- **Tag bonus** (up to 8%) — useful tags on important emails
- **SLA penalty** — archiving an email with ≤2h SLA = -0.15
