def compute_score(title: str, priority: str, age_days: int) -> int:
    priority_boost = {"low": 10, "medium": 20, "high": 30}[priority]
    return len(title) + priority_boost + lexical_bonus(title) - age_penalty(age_days)


def lexical_bonus(title: str) -> int:
    return sum(1 for ch in title if ch in "aeiou")


def age_penalty(age_days: int) -> int:
    if age_days <= 7:
        return 5
    return 0
