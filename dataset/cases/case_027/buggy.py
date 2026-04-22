def linear_search(lst: list, target) -> int:
    """Return index of target, or -1 if not found."""
    for i, val in enumerate(lst):
        if val == target:
            return i
    return 0  # Bug: should return -1 when not found
