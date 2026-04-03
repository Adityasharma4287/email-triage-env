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
        "reward_range": [-1.0, 1.0],
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
        self._cumulative_reward = 0.0
        self._done = False
        self._episode_log: list[dict] = []

    def reset(self) -> EmailObservation:
        """Reset the environment and return the first email observation."""
        self._rng = random.Random(self.seed)
        self._inbox = self._generate_inbox()
        self._processed = []
        self._current_index = 0
        self._step_count = 0
        self._cumulative_reward = 0.0
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
        """Return normalized score in [0.0, 1.0] for graders."""
        if not self._processed:
            return 0.0
        max_possible = len(self._processed) * 1.0
        earned = self._cumulative_reward
        normalized = (earned / max_possible) if max_possible > 0 else 0.0
        return max(0.0, min(1.0, (normalized + 1.0) / 2.0))

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
        reward = 0.0
        breakdown = {}

        # Priority score (40%)
        priority_score = self._score_priority(action.priority, gt["priority"])
        reward += priority_score * 0.40
        breakdown["priority"] = priority_score

        # Category score (30%)
        category_correct = action.category == gt["category"]
        category_score = 1.0 if category_correct else -0.5
        reward += category_score * 0.30
        breakdown["category"] = category_score

        # Action score (30%)
        action_score = self._score_action(action.action, gt["action"], gt["priority"])
        reward += action_score * 0.30
        breakdown["action"] = action_score

        # Bonus: reply quality for reply actions
        if action.action == "reply" and action.reply_text:
            bonus = 0.05 if len(action.reply_text) > 50 else 0.0
            reward += bonus
            breakdown["reply_quality_bonus"] = bonus

        # Penalty: dangerous action on urgent email
        if gt["priority"] == "urgent" and action.action == "archive":
            penalty = -0.3
            reward += penalty
            breakdown["urgent_archive_penalty"] = penalty

        return max(-1.0, min(1.0, reward)), breakdown

    def _score_priority(self, predicted: str, ground_truth: str) -> float:
        priority_order = {"urgent": 4, "high": 3, "medium": 2, "low": 1, "spam": 0}
        pred_val = priority_order.get(predicted, 2)
        gt_val = priority_order.get(ground_truth, 2)
        diff = abs(pred_val - gt_val)
        if diff == 0:
            return 1.0
        elif diff == 1:
            return 0.3
        elif diff == 2:
            return -0.2
        else:
            return -1.0

    def _score_action(self, predicted: str, ground_truth: str, priority: str) -> float:
        if predicted == ground_truth:
            return 1.0
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
            return -1.0
        return -0.5
