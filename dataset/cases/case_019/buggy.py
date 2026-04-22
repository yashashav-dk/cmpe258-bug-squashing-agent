def sum_up_to(n: int) -> int:
    """Return sum of integers 1..n inclusive."""
    total = 0
    for i in range(1, n):  # Bug: should be range(1, n+1)
        total += i
    return total
