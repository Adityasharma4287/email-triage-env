import json

def clamp_score(score):
    """
    Ensure score is strictly between 0 and 1 (not inclusive)
    """
    try:
        score = float(score)
    except:
        return 0.5  # safe fallback

    if score <= 0.0:
        return 0.01
    elif score >= 1.0:
        return 0.99
    return score


def inference(email):
    """
    Your main inference logic
    Replace this with your actual model logic if needed
    """

    # Example logic (replace with your model)
    tasks = [
        {"task": "spam", "score": 0.8},
        {"task": "important", "score": 0.6},
        {"task": "promotional", "score": 0.2}
    ]

    # 🔥 FIX: Clamp all scores
    for t in tasks:
        t["score"] = clamp_score(t["score"])

    return {"tasks": tasks}


if __name__ == "__main__":
    import sys

    try:
        input_data = sys.stdin.read()
        data = json.loads(input_data)

        email = data.get("email", "")

        result = inference(email)

        # 🔥 FINAL SAFETY CHECK
        for t in result.get("tasks", []):
            t["score"] = clamp_score(t.get("score", 0.5))

        print(json.dumps(result))

    except Exception as e:
        # Safe fallback output
        fallback = {
            "tasks": [
                {"task": "fallback", "score": 0.5}
            ]
        }
        print(json.dumps(fallback))
