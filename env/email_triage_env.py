"""
Email Triage OpenEnv Environment - ADVANCED v2.0
New: SLA tracking, Sentiment scoring, Custom tags, Snooze action,
     Difficulty ramp, Attachment types, Legal/HR categories
"""
import random
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Priority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SPAM = "spam"


class Category(str, Enum):
    CUSTOMER_SUPPORT = "customer_support"
    BILLING = "billing"
    TECHNICAL = "technical"
    SALES = "sales"
    INTERNAL = "internal"
    SPAM = "spam"
    LEGAL = "legal"
    HR = "hr"
    OTHER = "other"


class TriageAction(BaseModel):
    email_id: str
    priority: Priority
    category: Category
    action: str = Field(..., description="reply|archive|escalate|delete|forward|snooze")
    reply_text: Optional[str] = None
    forward_to: Optional[str] = None
    notes: Optional[str] = None
    custom_tags: Optional[list[str]] = Field(default_factory=list)
    snooze_hours: Optional[int] = None


class EmailObservation(BaseModel):
    email_id: str
    subject: str
    sender: str
    body: str
    timestamp: str
    has_attachment: bool
    attachment_type: Optional[str] = None
    thread_length: int
    inbox_count: int
    processed_count: int
    current_score: float
    step_number: int
    sentiment_score: float = 0.0
    sla_hours: Optional[int] = None
    difficulty: str = "medium"
    language: str = "en"


class EnvironmentState(BaseModel):
    inbox: list[dict]
    processed: list[dict]
    current_email_index: int
    total_emails: int
    step_count: int
    cumulative_reward: float
    task_id: str
    done: bool
    sla_breaches: int = 0
    total_tags_used: int = 0
    avg_sentiment: float = 0.0


EMAIL_TEMPLATES = [
    {"subject": "URGENT: Payment declined - can't access my account!!!","sender": "angry.customer@gmail.com","body": "My payment keeps getting declined and now I can't log in. I have a presentation in 2 hours and need this fixed NOW. I will dispute the charge if this isn't resolved immediately.","ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},"difficulty": "easy","sentiment": -0.85,"sla_hours": 2,"attachment_type": None},
    {"subject": "Server is DOWN - production outage","sender": "cto@bigclient.com","body": "Our entire application is down. 50,000 users are affected. We traced it to your API returning 500 errors since 14:30 UTC. Need immediate response from your engineering team.","ground_truth": {"priority": "urgent", "category": "technical", "action": "escalate"},"difficulty": "easy","sentiment": -0.9,"sla_hours": 1,"attachment_type": None},
    {"subject": "Enterprise deal - ready to sign $500k contract","sender": "vp.procurement@fortune500.com","body": "We've completed our evaluation and are ready to move forward with the enterprise tier. I need the contract sent by EOD for our board approval tomorrow.","ground_truth": {"priority": "high", "category": "sales", "action": "forward"},"difficulty": "easy","sentiment": 0.6,"sla_hours": 8,"attachment_type": "contract"},
    {"subject": "Following up on demo last week","sender": "john.smith@midco.com","body": "Hi, following up on last week's demo. The team loved it! We have some questions about the API rate limits and data residency options for EU customers before we can proceed.","ground_truth": {"priority": "high", "category": "sales", "action": "reply"},"difficulty": "medium","sentiment": 0.5,"sla_hours": 24,"attachment_type": None},
    {"subject": "Question about API rate limits","sender": "developer@startup.io","body": "Hello, I'm building an integration with your API and noticed I'm hitting rate limits at 100 req/min. Is there a way to increase this? I'm on the Pro plan.","ground_truth": {"priority": "medium", "category": "technical", "action": "reply"},"difficulty": "medium","sentiment": 0.1,"sla_hours": 48,"attachment_type": None},
    {"subject": "Feature request: Dark mode","sender": "user123@email.com","body": "Would love to see dark mode added to the dashboard. It's hard to use late at night. Is this on your roadmap?","ground_truth": {"priority": "medium", "category": "customer_support", "action": "reply"},"difficulty": "medium","sentiment": 0.3,"sla_hours": None,"attachment_type": None},
    {"subject": "Team lunch this Friday","sender": "hr@company.com","body": "Hey everyone! We're doing team lunch this Friday at Olive Garden, 12:30pm. Please RSVP by Wednesday so we can make a reservation.","ground_truth": {"priority": "low", "category": "internal", "action": "archive"},"difficulty": "easy","sentiment": 0.7,"sla_hours": None,"attachment_type": None},
    {"subject": "Monthly newsletter - March 2026","sender": "newsletter@industry.com","body": "Read our latest roundup of AI industry news, funding rounds, and product launches from March 2026.","ground_truth": {"priority": "low", "category": "other", "action": "archive"},"difficulty": "easy","sentiment": 0.2,"sla_hours": None,"attachment_type": None},
    {"subject": "You've WON a $1000 Amazon gift card!!!","sender": "noreply@prize-claim-now.xyz","body": "Congratulations!! You have been SELECTED as our lucky winner. Click the link below within 24 hours to claim your FREE $1000 Amazon gift card!","ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},"difficulty": "easy","sentiment": 0.4,"sla_hours": None,"attachment_type": None},
    {"subject": "Verify your invoice #INV-2024-8821","sender": "billing@amaz0n-secure.net","body": "Dear Customer, your recent order requires verification. Please click here to confirm your payment details to avoid account suspension.","ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},"difficulty": "medium","sentiment": -0.2,"sla_hours": None,"attachment_type": None},
    {"subject": "Re: Re: Re: Contract renewal","sender": "legal@partner-corp.com","body": "As discussed in our call last month, attached are the revised terms. Section 7.3 has been updated to reflect the new liability caps. Please review and revert with any redlines by next Friday.","ground_truth": {"priority": "high", "category": "sales", "action": "forward"},"difficulty": "hard","sentiment": 0.1,"sla_hours": 120,"attachment_type": "contract"},
    {"subject": "Security concern","sender": "unknown@protonmail.com","body": "I found a potential SQL injection vulnerability in your login page. I was able to extract some user email addresses. Please respond with how you want to handle this responsibly. I am not asking for money.","ground_truth": {"priority": "urgent", "category": "technical", "action": "escalate"},"difficulty": "hard","sentiment": -0.3,"sla_hours": 4,"attachment_type": "screenshot"},
    {"subject": "Checking in","sender": "sarah.jones@customer.com","body": "Hi! Just checking in. It's been 2 weeks since I submitted my support ticket (#44821) about the data export issue and haven't heard back. My CEO is asking for the data by end of week.","ground_truth": {"priority": "high", "category": "customer_support", "action": "escalate"},"difficulty": "hard","sentiment": -0.5,"sla_hours": 24,"attachment_type": None},
    {"subject": "Action Required: Your account will be suspended in 24 hours","sender": "security-alert@paypa1-support.com","body": "Dear valued customer, we detected unusual activity on your account. Verify your identity immediately by clicking the secure link below.","ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},"difficulty": "hard","sentiment": -0.4,"sla_hours": None,"attachment_type": None},
    {"subject": "GDPR Data Subject Access Request — Response Required Within 30 Days","sender": "legal@euregulator.org","body": "This is a formal Data Subject Access Request under Article 15 of the GDPR. The data subject requests all personal data held by your organisation. You are legally required to respond within 30 calendar days.","ground_truth": {"priority": "high", "category": "legal", "action": "escalate"},"difficulty": "hard","sentiment": -0.1,"sla_hours": 720,"attachment_type": None},
    {"subject": "Performance Review Cycle Starts Next Monday","sender": "hr@company.com","body": "Hi team, Q2 performance review cycle begins next Monday. Please complete your self-assessments in Workday by April 25th.","ground_truth": {"priority": "low", "category": "hr", "action": "archive"},"difficulty": "easy","sentiment": 0.3,"sla_hours": None,"attachment_type": None},
    {"subject": "Charged twice for the same invoice — this is unacceptable","sender": "cfo@midmarket-corp.com","body": "We were charged $4,200 twice for invoice INV-2026-0312. I have attached the bank statements. If not resolved by Friday we will initiate a chargeback and escalate to our legal team.","ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},"difficulty": "medium","sentiment": -0.95,"sla_hours": 4,"attachment_type": "invoice"},
    {"subject": "Strategic Partnership Opportunity — Series B fintech startup","sender": "ceo@fintechrocket.io","body": "I'm the founder of FinTechRocket, a Series B startup with 200k users. We'd love to explore embedding your API. Seven-figure ARR opportunity. Available for a 30-min call this week?","ground_truth": {"priority": "high", "category": "sales", "action": "forward"},"difficulty": "medium","sentiment": 0.7,"sla_hours": 48,"attachment_type": None},
    {"subject": "Please cancel my subscription","sender": "user4821@gmail.com","body": "I'd like to cancel my Pro subscription immediately. It's too expensive. Please confirm cancellation and refund the current month. I've been a customer for 3 years.","ground_truth": {"priority": "high", "category": "billing", "action": "reply"},"difficulty": "medium","sentiment": -0.4,"sla_hours": 24,"attachment_type": None},
    {"subject": "Problema urgente con la facturacion","sender": "cliente@empresa-mx.com","body": "Hola, tengo un problema urgente con mi factura del mes pasado. Me cobraron el doble y necesito una solucion hoy mismo. Por favor contactenme lo antes posible.","ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},"difficulty": "hard","sentiment": -0.8,"sla_hours": 8,"attachment_type": None},
    {"subject": "Mandatory: Reset your password before EOD","sender": "it-security@company.com","body": "Due to a recent security audit, all employees must reset their passwords before end of day today. Accounts not updated will be temporarily locked.","ground_truth": {"priority": "high", "category": "internal", "action": "archive"},"difficulty": "medium","sentiment": 0.0,"sla_hours": 8,"attachment_type": None},
    {"subject": "Just wanted to say thank you!","sender": "happy.customer@email.com","body": "Your support team was incredibly helpful in resolving my issue yesterday. I've been using your product for 2 years and this was my best experience yet!","ground_truth": {"priority": "low", "category": "customer_support", "action": "archive"},"difficulty": "easy","sentiment": 0.98,"sla_hours": None,"attachment_type": None},
    {"subject": "Invoice #V-20260401 from CloudHostPro — $899/month","sender": "billing@cloudhostpro.com","body": "Please find attached your monthly invoice for cloud hosting services. Amount due: $899.00. Payment is due within 15 days.","ground_truth": {"priority": "medium", "category": "billing", "action": "archive"},"difficulty": "easy","sentiment": 0.2,"sla_hours": 360,"attachment_type": "invoice"},
    {"subject": "Lawsuit threat — demand letter enclosed","sender": "attorney@legalfirm-ny.com","body": "On behalf of our client Mr. John Doe, we are formally demanding $25,000 in damages for unauthorized use of intellectual property. You have 14 days to respond before we file in federal court.","ground_truth": {"priority": "urgent", "category": "legal", "action": "escalate"},"difficulty": "hard","sentiment": -0.9,"sla_hours": 24,"attachment_type": "contract"},
    {"subject": "Data breach notification — immediate action required","sender": "security@trustedvendor.com","body": "We regret to inform you that our systems experienced a security incident on April 28, 2026. Your email address may have been exposed. We recommend changing your password immediately.","ground_truth": {"priority": "high", "category": "technical", "action": "escalate"},"difficulty": "hard","sentiment": -0.6,"sla_hours": 12,"attachment_type": None},
]


class EmailTriageEnv:
    metadata = {
        "name": "email-triage-v2",
        "version": "2.0.0",
        "description": "Advanced email triage with SLA, sentiment, tags, snooze",
        "reward_range": [-0.999, 0.999],
        "max_steps": 50,
        "new_features": ["sla_tracking", "sentiment_scoring", "custom_tags", "snooze_action", "difficulty_ramp", "legal_hr_categories"],
    }
    VALID_ACTIONS = {"reply", "archive", "escalate", "delete", "forward", "snooze"}

    def __init__(self, task_id="task_medium_triage", num_emails=10, seed=42, difficulty_ramp=False):
        self.task_id = task_id
        self.num_emails = num_emails
        self.seed = seed
        self.difficulty_ramp = difficulty_ramp
        self._rng = random.Random(seed)
        self._inbox = []
        self._processed = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0
        self._done = False
        self._episode_log = []
        self._sla_breaches = 0
        self._total_tags_used = 0
        self._sentiment_sum = 0.0

    def reset(self):
        self._rng = random.Random(self.seed)
        self._inbox = self._generate_inbox()
        self._processed = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0
        self._done = False
        self._episode_log = []
        self._sla_breaches = 0
        self._total_tags_used = 0
        self._sentiment_sum = 0.0
        return self._make_observation()

    def step(self, action):
        if self._done:
            raise RuntimeError("Episode done. Call reset().")
        current_email = self._inbox[self._current_index]
        reward, breakdown = self._compute_reward(action, current_email)
        self._cumulative_reward += reward
        self._sentiment_sum += current_email.get("sentiment", 0.0)
        if action.custom_tags:
            self._total_tags_used += len(action.custom_tags)
        sla = current_email.get("sla_hours")
        if sla is not None and sla <= 2 and action.action == "archive":
            self._sla_breaches += 1
            penalty = -0.15
            reward = max(-0.999, min(0.999, reward + penalty))
            breakdown["sla_breach_penalty"] = penalty
        self._episode_log.append({
            "step": self._step_count, "email_id": action.email_id,
            "subject": current_email["subject"], "ground_truth": current_email["ground_truth"],
            "agent_action": {"priority": action.priority, "category": action.category,
                             "action": action.action, "custom_tags": action.custom_tags or []},
            "reward": reward, "reward_breakdown": breakdown,
            "sentiment": current_email.get("sentiment", 0.0), "sla_hours": current_email.get("sla_hours"),
        })
        self._processed.append({**current_email, "agent_action": action.model_dump(), "reward": reward})
        self._step_count += 1
        self._current_index += 1
        if self._current_index >= len(self._inbox):
            self._done = True
        info = {
            "reward_breakdown": breakdown, "ground_truth": current_email["ground_truth"],
            "cumulative_reward": self._cumulative_reward,
            "emails_remaining": len(self._inbox) - self._current_index,
            "step": self._step_count, "sla_breaches": self._sla_breaches,
            "sentiment": current_email.get("sentiment", 0.0),
        }
        return self._make_observation(), round(reward, 4), self._done, info

    def state(self):
        avg_sent = self._sentiment_sum / max(1, self._step_count)
        return EnvironmentState(
            inbox=self._inbox, processed=self._processed,
            current_email_index=self._current_index, total_emails=len(self._inbox),
            step_count=self._step_count, cumulative_reward=self._cumulative_reward,
            task_id=self.task_id, done=self._done,
            sla_breaches=self._sla_breaches, total_tags_used=self._total_tags_used,
            avg_sentiment=round(avg_sent, 3),
        )

    def get_score(self):
        if not self._processed:
            return 0.001
        raw = ((self._cumulative_reward / len(self._processed)) + 1.0) / 2.0
        return max(0.001, min(0.999, round(raw, 4)))

    def get_episode_log(self):
        return self._episode_log

    @property
    def cumulative_reward(self): return self._cumulative_reward
    @property
    def is_done(self): return self._done
    @property
    def step_count(self): return self._step_count
    def current_observation(self): return self._make_observation()

    def _generate_inbox(self):
        templates = list(EMAIL_TEMPLATES)
        self._rng.shuffle(templates)
        if "easy" in self.task_id:
            templates = sorted(templates, key=lambda t: 0 if t["difficulty"]=="easy" else 1)
        elif "hard" in self.task_id:
            templates = sorted(templates, key=lambda t: 0 if t["difficulty"]=="hard" else (1 if t["difficulty"]=="medium" else 2))
        selected = templates[:self.num_emails]
        if self.difficulty_ramp:
            d = {"easy": 0, "medium": 1, "hard": 2}
            selected.sort(key=lambda x: d.get(x["difficulty"], 1))
        inbox = []
        for i, tmpl in enumerate(selected):
            inbox.append({
                **tmpl, "email_id": f"email_{i+1:03d}",
                "timestamp": f"2026-04-28T{9+i:02d}:00:00Z",
                "has_attachment": tmpl.get("attachment_type") is not None or self._rng.random() < 0.2,
                "thread_length": self._rng.randint(1, 5),
                "language": "es" if "facturacion" in tmpl.get("subject","") else "en",
            })
        return inbox

    def _make_observation(self):
        if self._done or self._current_index >= len(self._inbox):
            return EmailObservation(
                email_id="DONE", subject="", sender="", body="", timestamp="",
                has_attachment=False, thread_length=0, inbox_count=0,
                processed_count=len(self._processed), current_score=self.get_score(),
                step_number=self._step_count,
            )
        e = self._inbox[self._current_index]
        return EmailObservation(
            email_id=e["email_id"], subject=e["subject"], sender=e["sender"],
            body=e["body"], timestamp=e["timestamp"], has_attachment=e["has_attachment"],
            attachment_type=e.get("attachment_type"), thread_length=e["thread_length"],
            inbox_count=len(self._inbox)-self._current_index,
            processed_count=len(self._processed), current_score=self.get_score(),
            step_number=self._step_count, sentiment_score=e.get("sentiment", 0.0),
            sla_hours=e.get("sla_hours"), difficulty=e.get("difficulty","medium"),
            language=e.get("language","en"),
        )

    def _compute_reward(self, action, email):
        gt = email["ground_truth"]
        reward, breakdown = 0.0, {}
        ps = self._score_priority(action.priority, gt["priority"])
        reward += ps * 0.35; breakdown["priority"] = ps
        cs = 0.999 if action.category == gt["category"] else -0.5
        reward += cs * 0.25; breakdown["category"] = cs
        as_ = self._score_action(action.action, gt["action"], gt["priority"])
        reward += as_ * 0.30; breakdown["action"] = as_
        sentiment = email.get("sentiment", 0.0)
        if sentiment < -0.6 and action.action in ("escalate","reply") and gt["priority"] in ("urgent","high"):
            reward += 0.08; breakdown["sentiment_angry_bonus"] = 0.08
        elif sentiment > 0.8 and action.action == "archive":
            reward += 0.03; breakdown["sentiment_positive_bonus"] = 0.03
        if action.custom_tags:
            useful = [t for t in action.custom_tags if t.lower() in ("vip","legal-review","follow-up","churn-risk")]
            if useful and gt["priority"] in ("urgent","high"):
                b = 0.04*min(len(useful),2); reward += b; breakdown["tag_bonus"] = b
        if action.action == "reply" and action.reply_text:
            b = 0.05 if len(action.reply_text) > 50 else -0.02
            reward += b; breakdown["reply_quality_bonus"] = b
        if gt["priority"] == "urgent" and action.action == "archive":
            reward += -0.35; breakdown["urgent_archive_penalty"] = -0.35
        if action.action == "delete" and gt["priority"] in ("urgent","high"):
            reward += -0.4; breakdown["delete_important_penalty"] = -0.4
        return round(max(-0.999, min(0.999, reward)), 4), breakdown

    def _score_priority(self, predicted, ground_truth):
        order = {"urgent":4,"high":3,"medium":2,"low":1,"spam":0}
        diff = abs(order.get(str(predicted),2) - order.get(ground_truth,2))
        return [0.999, 0.3, -0.2, -0.999][min(diff, 3)]

    def _score_action(self, predicted, ground_truth, priority):
        if predicted == ground_truth: return 0.999
        if predicted == "snooze" and priority in ("low","medium"): return 0.3
        alts = {"escalate":["forward","reply"],"forward":["escalate"],"reply":["escalate","forward"],"archive":["delete"],"delete":["archive"]}
        if predicted in alts.get(ground_truth, []): return 0.4
        if predicted == "delete" and priority in ("urgent","high"): return -0.999
        return -0.5
