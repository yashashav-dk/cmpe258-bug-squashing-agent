from system.gateway import summarize_order


def quote(order: dict) -> float:
    return summarize_order(order)
