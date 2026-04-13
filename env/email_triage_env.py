"""
Email Triage OpenEnv Environment
Simulates a real-world email inbox management task for AI agents.
"""
import random
import json
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# ─── Action & Observation Models ──────────────────────────────────────────────

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
    OTHER = "other"


class TriageAction(BaseModel):
    email_id: str = Field(..., description="ID of the email to triage")
    priority: Priority = Field(..., description="Assigned priority level")
    category: Category = Field(..., description="Assigned category")
    action: str = Field(..., description="Action: reply|archive|escalate|delete|forward")
    reply_text: Optional[str] = Field(None, description="Reply content if action is reply")
    forward_to: Optional[str] = Field(None, description="Email to forward to if action is forward")
    notes: Optional[str] = Field(None, description="Agent notes about this email")


class EmailObservation(BaseModel):
    email_id: str
    subject: str
    sender: str
    body: str
    timestamp: str
    has_attachment: bool
    thread_length: int
    inbox_count: int = Field(..., description="Remaining emails to process")
    processed_count: int
    current_score: float
    step_number: int


class EnvironmentState(BaseModel):
    inbox: list[dict]
    processed: list[dict]
    current_email_index: int
    total_emails: int
    step_count: int
    cumulative_reward: float
    task_id: str
    done: bool


# ─── Email Dataset ─────────────────────────────────────────────────────────────

EMAIL_TEMPLATES = [
    # URGENT - Customer Support
    {
        "subject": "URGENT: Payment declined - can't access my account!!!",
        "sender": "angry.customer@gmail.com",
        "body": "My payment keeps getting declined and now I can't log in. I have a presentation in 2 hours and need this fixed NOW. I will dispute the charge if this isn't resolved immediately.",
        "ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},
        "difficulty": "easy"
    },
    {
        "subject": "Server is DOWN - production outage",
        "sender": "cto@bigclient.com",
        "body": "Our entire application is down. 50,000 users are affected. We traced it to your API returning 500 errors since 14:30 UTC. Need immediate response from your engineering team.",
        "ground_truth": {"priority": "urgent", "category": "technical", "action": "escalate"},
        "difficulty": "easy"
    },
    # HIGH - Sales
    {
        "subject": "Enterprise deal - ready to sign $500k contract",
        "sender": "vp.procurement@fortune500.com",
        "body": "We've completed our evaluation and are ready to move forward with the enterprise tier. I need the contract sent by EOD for our board approval tomorrow. Please also include SLA guarantees.",
        "ground_truth": {"priority": "high", "category": "sales", "action": "forward"},
        "difficulty": "easy"
    },
    {
        "subject": "Following up on demo last week",
        "sender": "john.smith@midco.com",
        "body": "Hi, following up on last week's demo. The team loved it! We have some questions about the API rate limits and data residency options for EU customers before we can proceed.",
        "ground_truth": {"priority": "high", "category": "sales", "action": "reply"},
        "difficulty": "medium"
    },
    # MEDIUM - Technical
    {
        "subject": "Question about API rate limits",
        "sender": "developer@startup.io",
        "body": "Hello, I'm building an integration with your API and noticed I'm hitting rate limits at 100 req/min. Is there a way to increase this? I'm on the Pro plan. Also, do you support webhook retries?",
        "ground_truth": {"priority": "medium", "category": "technical", "action": "reply"},
        "difficulty": "medium"
    },
    {
        "subject": "Feature request: Dark mode",
        "sender": "user123@email.com",
        "body": "Would love to see dark mode added to the dashboard. It's hard to use late at night. Is this on your roadmap? Would pay extra for it honestly.",
        "ground_truth": {"priority": "medium", "category": "customer_support", "action": "reply"},
        "difficulty": "medium"
    },
    # LOW - Internal / Routine
    {
        "subject": "Team lunch this Friday",
        "sender": "hr@company.com",
        "body": "Hey everyone! We're doing team lunch this Friday at Olive Garden, 12:30pm. Please RSVP by Wednesday so we can make a reservation. All expenses covered!",
        "ground_truth": {"priority": "low", "category": "internal", "action": "archive"},
        "difficulty": "easy"
    },
    {
        "subject": "Monthly newsletter - March 2026",
        "sender": "newsletter@industry.com",
        "body": "Read our latest roundup of AI industry news, funding rounds, and product launches from March 2026. Click here to read the full issue online.",
        "ground_truth": {"priority": "low", "category": "other", "action": "archive"},
        "difficulty": "easy"
    },
    # SPAM
    {
        "subject": "You've WON a $1000 Amazon gift card!!!",
        "sender": "noreply@prize-claim-now.xyz",
        "body": "Congratulations!! You have been SELECTED as our lucky winner. Click the link below within 24 hours to claim your FREE $1000 Amazon gift card. Limited time offer!!!",
        "ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},
        "difficulty": "easy"
    },
    {
        "subject": "Verify your invoice #INV-2024-8821",
        "sender": "billing@amaz0n-secure.net",
        "body": "Dear Customer, your recent order requires verification. Please click here to confirm your payment details to avoid account suspension. Act within 48 hours.",
        "ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},
        "difficulty": "medium"
    },
    # HARD - Ambiguous cases
    {
        "subject": "Re: Re: Re: Contract renewal",
        "sender": "legal@partner-corp.com",
        "body": "As discussed in our call last month, attached are the revised terms. Section 7.3 has been updated to reflect the new liability caps. Please review and revert with any redlines by next Friday. Also, happy to jump on a call if needed.",
        "ground_truth": {"priority": "high", "category": "sales", "action": "forward"},
        "difficulty": "hard"
    },
    {
        "subject": "Security concern",
        "sender": "unknown@protonmail.com",
        "body": "I found a potential SQL injection vulnerability in your login page. I was able to extract some user email addresses. Please respond with how you want to handle this responsibly. I am not asking for money.",
        "ground_truth": {"priority": "urgent", "category": "technical", "action": "escalate"},
        "difficulty": "hard"
    },
    {
        "subject": "Checking in",
        "sender": "sarah.jones@customer.com",
        "body": "Hi! Just checking in. It's been 2 weeks since I submitted my support ticket (#44821) about the data export issue and haven't heard back. My CEO is asking for the data by end of week.",
        "ground_truth": {"priority": "high", "category": "customer_support", "action": "escalate"},
        "difficulty": "hard"
    },

    # ── NEW TEMPLATES (diverse & realistic) ────────────────────────────────────

    # Phishing — looks real but isn't
    {
        "subject": "Action Required: Your account will be suspended in 24 hours",
        "sender": "security-alert@paypa1-support.com",
        "body": "Dear valued customer, we detected unusual activity on your PayPal account. To avoid suspension, verify your identity immediately by clicking the secure link below. Failure to do so will result in permanent account closure.",
        "ground_truth": {"priority": "spam", "category": "spam", "action": "delete"},
        "difficulty": "hard"
    },

    # Legal / Compliance — needs immediate routing
    {
        "subject": "GDPR Data Subject Access Request — Response Required Within 30 Days",
        "sender": "legal@euregulator.org",
        "body": "This is a formal Data Subject Access Request under Article 15 of the GDPR. The data subject requests all personal data held by your organisation. You are legally required to respond within 30 calendar days. Please confirm receipt and provide the data or a valid exemption notice.",
        "ground_truth": {"priority": "high", "category": "other", "action": "escalate"},
        "difficulty": "hard"
    },

    # HR — low priority internal
    {
        "subject": "Performance Review Cycle Starts Next Monday",
        "sender": "hr@company.com",
        "body": "Hi team, just a reminder that our Q2 performance review cycle begins next Monday. Please complete your self-assessments in Workday by April 25th. If you have questions, reach out to your HR business partner.",
        "ground_truth": {"priority": "low", "category": "internal", "action": "archive"},
        "difficulty": "easy"
    },

    # Billing dispute — angry CFO
    {
        "subject": "Charged twice for the same invoice — this is unacceptable",
        "sender": "cfo@midmarket-corp.com",
        "body": "We were charged $4,200 twice for invoice INV-2026-0312. I have attached the bank statements. This is a serious error and if not resolved by Friday we will initiate a chargeback and escalate to our legal team. I expect a response within the hour.",
        "ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},
        "difficulty": "medium"
    },

    # Partnership inquiry — high value sales lead
    {
        "subject": "Strategic Partnership Opportunity — Series B fintech startup",
        "sender": "ceo@fintechrocket.io",
        "body": "Hi, I'm the founder of FinTechRocket, a Series B startup with 200k users. We'd love to explore embedding your API into our product. We believe this could be a seven-figure ARR opportunity for both sides. Are you available for a 30-min call this week?",
        "ground_truth": {"priority": "high", "category": "sales", "action": "forward"},
        "difficulty": "medium"
    },

    # Subscription cancellation — churn risk
    {
        "subject": "Please cancel my subscription",
        "sender": "user4821@gmail.com",
        "body": "I'd like to cancel my Pro subscription immediately. It's too expensive and I'm not using most of the features. Please confirm cancellation and refund the current month. I've been a customer for 3 years.",
        "ground_truth": {"priority": "high", "category": "billing", "action": "reply"},
        "difficulty": "medium"
    },

    # Multi-language — Spanish (tests robustness)
    {
        "subject": "Problema urgente con la facturacion",
        "sender": "cliente@empresa-mx.com",
        "body": "Hola, tengo un problema urgente con mi factura del mes pasado. Me cobraron el doble y necesito una solucion hoy mismo. Por favor contactenme lo antes posible. Gracias.",
        "ground_truth": {"priority": "urgent", "category": "billing", "action": "escalate"},
        "difficulty": "hard"
    },

    # IT security — internal mandatory action
    {
        "subject": "Mandatory: Reset your password before EOD",
        "sender": "it-security@company.com",
        "body": "Due to a recent security audit, all employees must reset their passwords before end of day today. Please visit the IT portal and follow the instructions. Accounts that are not updated will be temporarily locked.",
        "ground_truth": {"priority": "high", "category": "internal", "action": "archive"},
        "difficulty": "medium"
    },

    # Positive feedback — no action needed
    {
        "subject": "Just wanted to say thank you!",
        "sender": "happy.customer@email.com",
        "body": "Your support team (especially Alex) was incredibly helpful in resolving my issue yesterday. I've been using your product for 2 years and this was my best experience yet. Keep up the great work!",
        "ground_truth": {"priority": "low", "category": "customer_support", "action": "archive"},
        "difficulty": "easy"
    },

    # Vendor invoice — routine billing
    {
        "subject": "Invoice #V-20260401 from CloudHostPro — $899/month",
        "sender": "billing@cloudhostpro.com",
        "body": "Please find attached your monthly invoice for cloud hosting services. Amount due: $899.00. Payment is due within 15 days. Thank you for your continued business.",
        "ground_truth": {"priority": "medium", "category": "billing", "action": "archive"},
        "difficulty": "easy"
    },
]


# ─── Environment ───────────────────────────────────────────────────────────────

class EmailTriageEnv:
    """
    OpenEnv-compliant Email Triage Environment.
    
    An AI agent receives emails one at a time and must:
    1. Assign the correct priority level
    2. Categorize the email correctly
    3. Choose the appropriate action (reply/archive/escalate/delete/forward)
    
    Rewards are given for correct decisions and penalized for mistakes.
    """

    metadata = {
        "name": "email-triage-v1",
        "version": "1.0.0",
        "description": "Real-world email inbox triage environment for AI agents",
        "author": "OpenEnv Hackathon",
        "tags": ["email", "triage", "nlp", "customer-support"],
        "action_space": "TriageAction (Pydantic model)",
        "observation_space": "EmailObservation (Pydantic model)",
        "reward_range": [-0.999, 0.999],
        "max_steps": 50,
    }

    VALID_ACTIONS = {"reply", "archive", "escalate", "delete", "forward"}

    def __init__(self, task_id: str = "task_medium", num_emails: int = 10, seed: int = 42):
        self.task_id = task_id
        self.num_emails = num_emails
        self.seed = seed
        self._rng = random.Random(seed)
        self._inbox: list[dict] = []
        self._processed: list[dict] = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0  # internal accumulator, not a score
        self._done = False
        self._episode_log: list[dict] = []

    def reset(self) -> EmailObservation:
        """Reset the environment and return the first email observation."""
        self._rng = random.Random(self.seed)
        self._inbox = self._generate_inbox()
        self._processed = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0  # internal accumulator, not a score
        self._done = False
        self._episode_log = []
        return self._make_observation()

    def step(self, action: TriageAction) -> tuple[EmailObservation, float, bool, dict]:
        """
        Process a triage action for the current email.
        
        Returns:
            observation: Next email observation (or terminal obs if done)
            reward: Float in [-1.0, 1.0]
            done: Whether the episode is complete
            info: Diagnostic information
        """
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        current_email = self._inbox[self._current_index]
        reward, reward_breakdown = self._compute_reward(action, current_email)
        self._cumulative_reward += reward

        # Log this step
        log_entry = {
            "step": self._step_count,
            "email_id": action.email_id,
            "subject": current_email["subject"],
            "ground_truth": current_email["ground_truth"],
            "agent_action": {
                "priority": action.priority,
                "category": action.category,
                "action": action.action,
            },
            "reward": reward,
            "reward_breakdown": reward_breakdown,
        }
        self._episode_log.append(log_entry)
        self._processed.append({**current_email, "agent_action": action.model_dump(), "reward": reward})

        self._step_count += 1
        self._current_index += 1

        # Check termination
        if self._current_index >= len(self._inbox):
            self._done = True

        info = {
            "reward_breakdown": reward_breakdown,
            "ground_truth": current_email["ground_truth"],
            "cumulative_reward": self._cumulative_reward,
            "emails_remaining": len(self._inbox) - self._current_index,
            "step": self._step_count,
        }

        obs = self._make_observation()
        return obs, reward, self._done, info

    def state(self) -> EnvironmentState:
        """Return the full current state of the environment."""
        return EnvironmentState(
            inbox=self._inbox,
            processed=self._processed,
            current_email_index=self._current_index,
            total_emails=len(self._inbox),
            step_count=self._step_count,
            cumulative_reward=self._cumulative_reward,
            task_id=self.task_id,
            done=self._done,
        )

    def get_score(self) -> float:
        """Return normalized score strictly in (0.0, 1.0) exclusive for graders."""
        if not self._processed:
            return 0.001
        max_possible = len(self._processed) * 1.0
        earned = self._cumulative_reward
        normalized = (earned / max_possible) if max_possible > 0 else -0.999
        raw = (normalized + 1.0) / 2.0
        # Clamp to strictly (0, 1) — 0.0 and 1.0 are not allowed
        if raw <= 0.0:
            return 0.001
        elif raw >= 1.0:
            return 0.999
        return round(raw, 4)

    def get_episode_log(self) -> list[dict]:  # type: ignore[type-arg]
        return self._episode_log

    # ── Public read-only properties (avoids Pylance protected-access warning) ──

    @property
    def cumulative_reward(self) -> float:
        return self._cumulative_reward

    @property
    def is_done(self) -> bool:
        return self._done

    @property
    def step_count(self) -> int:
        return self._step_count

    def current_observation(self) -> "EmailObservation":
        """Public wrapper around _make_observation() for external callers."""
        return self._make_observation()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _generate_inbox(self) -> list[dict]:
        """Generate a randomized inbox from templates."""
        templates = list(EMAIL_TEMPLATES)
        self._rng.shuffle(templates)
        selected = templates[:self.num_emails]
        inbox = []
        for i, tmpl in enumerate(selected):
            email = {
                **tmpl,
                "email_id": f"email_{i+1:03d}",
                "timestamp": f"2026-03-31T{9+i:02d}:00:00Z",
                "has_attachment": self._rng.random() < 0.3,
                "thread_length": self._rng.randint(1, 5),
            }
            inbox.append(email)
        return inbox

    def _make_observation(self) -> EmailObservation:
        if self._done or self._current_index >= len(self._inbox):
            # Terminal observation (empty sentinel)
            return EmailObservation(
                email_id="DONE",
                subject="",
                sender="",
                body="",
                timestamp="",
                has_attachment=False,
                thread_length=0,
                inbox_count=0,
                processed_count=len(self._processed),
                current_score=self.get_score(),
                step_number=self._step_count,
            )
        email = self._inbox[self._current_index]
        return EmailObservation(
            email_id=email["email_id"],
            subject=email["subject"],
            sender=email["sender"],
            body=email["body"],
            timestamp=email["timestamp"],
            has_attachment=email["has_attachment"],
            thread_length=email["thread_length"],
            inbox_count=len(self._inbox) - self._current_index,
            processed_count=len(self._processed),
            current_score=self.get_score(),
            step_number=self._step_count,
        )

    def _compute_reward(self, action: TriageAction, email: dict) -> tuple[float, dict]:
        """
        Compute reward for a triage decision. Returns value in [-1.0, 1.0].
        
        Reward is based on:
        - Priority correctness (40%)
        - Category correctness (30%)
        - Action appropriateness (30%)
        """
        gt = email["ground_truth"]
        reward = 0.0  # internal accumulator, not a score
        breakdown = {}

        # Priority score (40%)
        priority_score = self._score_priority(action.priority, gt["priority"])
        reward += priority_score * 0.40
        breakdown["priority"] = priority_score

        # Category score (30%)
        category_correct = action.category == gt["category"]
        category_score = 0.999 if category_correct else -0.5
        reward += category_score * 0.30
        breakdown["category"] = category_score

        # Action score (30%)
        action_score = self._score_action(action.action, gt["action"], gt["priority"])
        reward += action_score * 0.30
        breakdown["action"] = action_score

        # Bonus: reply quality for reply actions
        if action.action == "reply" and action.reply_text:
            bonus = 0.05 if len(action.reply_text) > 50 else -0.999
            reward += bonus
            breakdown["reply_quality_bonus"] = bonus

        # Penalty: dangerous action on urgent email
        if gt["priority"] == "urgent" and action.action == "archive":
            penalty = -0.3
            reward += penalty
            breakdown["urgent_archive_penalty"] = penalty

        clamped = max(-0.999, min(0.999, reward))
        return round(clamped, 4), breakdown

    def _score_priority(self, predicted: str, ground_truth: str) -> float:
        priority_order = {"urgent": 4, "high": 3, "medium": 2, "low": 1, "spam": 0}
        pred_val = priority_order.get(predicted, 2)
        gt_val = priority_order.get(ground_truth, 2)
        diff = abs(pred_val - gt_val)
        if diff == 0:
            return 0.999
        elif diff == 1:
            return 0.3
        elif diff == 2:
            return -0.2
        else:
            return -0.999

    def _score_action(self, predicted: str, ground_truth: str, priority: str) -> float:
        if predicted == ground_truth:
            return 0.999
        # Partial credit for reasonable alternatives
        reasonable_alts = {
            "escalate": ["forward", "reply"],
            "forward": ["escalate"],
            "reply": ["escalate", "forward"],
            "archive": ["delete"],
            "delete": ["archive"],
        }
        alts = reasonable_alts.get(ground_truth, [])
        if predicted in alts:
            return 0.4
        # Heavy penalty for deleting non-spam urgent/high
        if predicted == "delete" and priority in ("urgent", "high"):
            return -0.999
        return -0.5
