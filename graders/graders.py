"""
Task Graders for Email Triage Environment
Each grader scores agent performance on 0.0 - 1.0 scale.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from env.email_triage_env import EmailTriageEnv, TriageAction, Priority, Category


# ─── Score Normalization (strictly between 0 and 1, exclusive) ────────────────

def normalize_score(score: float) -> float:
    """Clamp score to strictly (0, 1) — 0.0 and 1.0 are not allowed."""
    if score <= 0:
        return 0.001
    elif score >= 1:
        return 0.999
    return round(score, 4)


# ─── Base Grader ──────────────────────────────────────────────────────────────

class BaseGrader:
    task_id: str
    description: str
    difficulty: str
    num_emails: int
    seed: int

    def run(self, agent_actions: list[dict]) -> dict:
        """
        Run grader with provided agent actions.
        Returns dict with score, details, and pass/fail per criterion.
        """
        env = EmailTriageEnv(task_id=self.task_id, num_emails=self.num_emails, seed=self.seed)
        obs = env.reset()

        results = []
        for action_dict in agent_actions:
            if obs.email_id == "DONE":
                break
            try:
                action = TriageAction(
                    email_id=obs.email_id,
                    priority=action_dict.get("priority", "medium"),
                    category=action_dict.get("category", "other"),
                    action=action_dict.get("action", "archive"),
                    reply_text=action_dict.get("reply_text"),
                    forward_to=action_dict.get("forward_to"),
                    notes=action_dict.get("notes"),
                )
                obs, reward, done, info = env.step(action)
                results.append({"reward": reward, "info": info})
                if done:
                    break
            except Exception as e:
                results.append({"reward": -0.5, "info": {"error": str(e)}})

        raw_score = env.get_score()
        score = normalize_score(raw_score)  # ← FIX: ensure strictly (0, 1)
        episode_log = env.get_episode_log()

        return {
            "score": score,
            "task_id": self.task_id,
            "difficulty": self.difficulty,
            "description": self.description,
            "emails_processed": len(episode_log),
            "passed": score >= self.passing_threshold,
            "episode_log": episode_log,
            "criteria": self._evaluate_criteria(episode_log, score),
        }

    def _evaluate_criteria(self, log: list[dict], score: float) -> dict:
        raise NotImplementedError


# ─── Task 1: Easy — Spam & Priority Detection ─────────────────────────────────

class SpamDetectionGrader(BaseGrader):
    task_id = "task_easy_spam"
    description = "Detect spam emails and assign basic priority levels. Tests fundamental triage on clear-cut cases."
    difficulty = "easy"
    num_emails = 5
    seed = 42
    passing_threshold = 0.60

    def _evaluate_criteria(self, log: list[dict], score: float) -> dict:
        spam_correct = 0
        spam_total = 0
        urgent_correct = 0
        urgent_total = 0

        for entry in log:
            gt = entry["ground_truth"]
            agent = entry["agent_action"]

            if gt["priority"] == "spam":
                spam_total += 1
                if agent["priority"] == "spam" and agent["action"] == "delete":
                    spam_correct += 1

            if gt["priority"] == "urgent":
                urgent_total += 1
                if agent["priority"] == "urgent":
                    urgent_correct += 1

        return {
            "spam_detection_rate": round(spam_correct / spam_total, 3) if spam_total else 1.0,
            "urgent_detection_rate": round(urgent_correct / urgent_total, 3) if urgent_total else 1.0,
            "overall_score": score,
            "passed": score >= self.passing_threshold,
        }


# ─── Task 2: Medium — Full Triage Pipeline ────────────────────────────────────

class FullTriageGrader(BaseGrader):
    task_id = "task_medium_triage"
    description = "Complete email triage: priority, category, and action across all email types. Mixed difficulty inbox."
    difficulty = "medium"
    num_emails = 10
    seed = 99
    passing_threshold = 0.55

    def _evaluate_criteria(self, log: list[dict], score: float) -> dict:
        priority_hits = sum(
            1 for e in log if e["agent_action"]["priority"] == e["ground_truth"]["priority"]
        )
        category_hits = sum(
            1 for e in log if e["agent_action"]["category"] == e["ground_truth"]["category"]
        )
        action_hits = sum(
            1 for e in log if e["agent_action"]["action"] == e["ground_truth"]["action"]
        )
        n = len(log) or 1
        return {
            "priority_accuracy": round(priority_hits / n, 3),
            "category_accuracy": round(category_hits / n, 3),
            "action_accuracy": round(action_hits / n, 3),
            "overall_score": score,
            "passed": score >= self.passing_threshold,
        }


# ─── Task 3: Hard — Edge Cases & Ambiguous Emails ─────────────────────────────

class AmbiguousEmailGrader(BaseGrader):
    task_id = "task_hard_ambiguous"
    description = "Handle ambiguous emails: security disclosures, long threads, polite-but-urgent complaints. Tests reasoning depth."
    difficulty = "hard"
    num_emails = 13
    seed = 777
    passing_threshold = 0.45

    def _evaluate_criteria(self, log: list[dict], score: float) -> dict:
        hard_emails = [e for e in log]
        dangerous_mistakes = sum(
            1 for e in hard_emails
            if e["ground_truth"]["priority"] == "urgent"
            and e["agent_action"]["action"] in ("archive", "delete")
        )
        escalations = sum(1 for e in hard_emails if e["agent_action"]["action"] == "escalate")
        gt_escalations = sum(1 for e in hard_emails if e["ground_truth"]["action"] == "escalate")

        return {
            "dangerous_mistakes": dangerous_mistakes,
            "no_dangerous_mistakes": dangerous_mistakes == 0,
            "escalation_precision": round(
                escalations / gt_escalations if gt_escalations else 1.0, 3
            ),
            "overall_score": score,
            "passed": score >= self.passing_threshold,
        }


# ─── Grader Registry ──────────────────────────────────────────────────────────

GRADERS = {
    "easy": SpamDetectionGrader(),
    "medium": FullTriageGrader(),
    "hard": AmbiguousEmailGrader(),
}


def run_all_graders(agent_fn) -> dict:
    """
    Run all three graders with an agent function.
    agent_fn receives an EmailObservation dict and returns an action dict.
    """
    from env.email_triage_env import EmailTriageEnv, TriageAction

    results = {}
    for difficulty, grader in GRADERS.items():
        env = EmailTriageEnv(
            task_id=grader.task_id,
            num_emails=grader.num_emails,
            seed=grader.seed,
        )
        obs = env.reset()
        actions = []
        while obs.email_id != "DONE":
            action_dict = agent_fn(obs.model_dump())
            actions.append(action_dict)
            action = TriageAction(
                email_id=obs.email_id,
                priority=action_dict.get("priority", "medium"),
                category=action_dict.get("category", "other"),
                action=action_dict.get("action", "archive"),
                reply_text=action_dict.get("reply_text"),
                forward_to=action_dict.get("forward_to"),
                notes=action_dict.get("notes"),
            )
            obs, _, done, _ = env.step(action)
            if done:
                break
        results[difficulty] = grader.run(actions)

    scores = [r["score"] for r in results.values()]
    results["summary"] = {
        "average_score": normalize_score(sum(scores) / len(scores)),  # ← FIX: normalize summary too
        "all_passed": all(r["passed"] for r in results.values()),
        "scores_by_difficulty": {k: results[k]["score"] for k in ["easy", "medium", "hard"]},
    }
    return results


if __name__ == "__main__":
    import json

    def dummy_agent(obs: dict) -> dict:
        """Baseline agent that always picks medium priority."""
        return {
            "priority": "medium",
            "category": "other",
            "action": "archive",
        }

    print("Running all graders with dummy agent...")
    results = run_all_graders(dummy_agent)
    print(json.dumps(results["summary"], indent=2))
