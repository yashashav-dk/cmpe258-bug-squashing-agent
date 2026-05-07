def normalize_title(title: str) -> str:
    return str(title).strip()


def normalize_priority(priority: str) -> str:
    value = str(priority).strip().lower()
    if value not in {"low", "medium", "high"}:
        raise ValueError("unknown priority")
    return value


def parse_age_days(value) -> int:
    age_days = int(value)
    if age_days < 0:
        raise ValueError("age_days must be >= 0")
    return age_days
