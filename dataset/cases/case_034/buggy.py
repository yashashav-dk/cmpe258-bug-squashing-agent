def binary_search(arr: list, target: int) -> int:
    """Binary search. Bug: lo = mid instead of lo = mid + 1 causes infinite loop on small arrays."""
    lo, hi = 0, len(arr) - 1
    steps = 0
    while lo <= hi and steps < 100:  # steps guard prevents infinite loop in tests
        steps += 1
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid  # Bug: should be mid + 1
        else:
            hi = mid - 1
    return -1
