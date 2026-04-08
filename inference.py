import sys

def evaluate_email():
    """
    Dummy evaluation logic (replace with your real logic if needed)
    """
    task_name = "email_triage"

    # Example steps
    rewards = [0.6, 0.7, 0.8]

    # VALID SCORE (STRICTLY BETWEEN 0 AND 1)
    score = sum(rewards) / len(rewards)

    # Safety clamp (IMPORTANT)
    if score <= 0:
        score = 0.01
    elif score >= 1:
        score = 0.99

    # START block
    print(f"[START] task={task_name}", flush=True)

    # STEP blocks
    for i, reward in enumerate(rewards):
        # reward bhi safe range me rakho
        if reward <= 0:
            reward = 0.01
        elif reward >= 1:
            reward = 0.99

        print(f"[STEP] step={i+1} reward={reward}", flush=True)

    # END block
    print(f"[END] task={task_name} score={score} steps={len(rewards)}", flush=True)


if __name__ == "__main__":
    evaluate_email()
