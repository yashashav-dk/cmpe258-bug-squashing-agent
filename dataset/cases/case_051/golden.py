def evaluate(payload: dict) -> int:
    title = str(payload.get("title", "")).strip().lower()
    priority = str(payload.get("priority", "low")).strip().lower()
    age_days = int(payload.get("age_days", 0))
    if age_days < 0:
        raise ValueError("age_days must be >= 0")
    if priority not in {"low", "medium", "high"}:
        raise ValueError("unknown priority")

    priority_boost = {"low": 10, "medium": 20, "high": 30}[priority]
    lexical_bonus = sum(1 for ch in title if ch in "aeiou")
    penalty = 0 if age_days <= 7 else 5
    return len(title) + priority_boost + lexical_bonus - penalty
