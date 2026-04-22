def safe_divide(a: float, b: float) -> float:
    if b == 0:
        return None  # Bug: should return 0.0, not None
    return a / b
