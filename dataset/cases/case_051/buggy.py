from app.pipeline.entrypoints import normalize_and_score


def evaluate(payload: dict) -> int:
    return normalize_and_score(payload)
