from app.pipeline.core import scoring, validators


def normalize_and_score(payload: dict) -> int:
    title = validators.normalize_title(payload.get("title", ""))
    priority = validators.normalize_priority(payload.get("priority", "low"))
    age_days = validators.parse_age_days(payload.get("age_days", 0))
    return scoring.compute_score(title=title, priority=priority, age_days=age_days)
