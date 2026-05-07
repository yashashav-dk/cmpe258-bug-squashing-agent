from system.domain.normalize import normalize_order
from system.domain.pricing.totals import compute_total


def summarize_order(order: dict) -> float:
    normalized = normalize_order(order)
    return compute_total(normalized)
