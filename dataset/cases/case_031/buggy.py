def max_subarray_sum(nums: list) -> int:
    """Kadane's algorithm. Bug: wrong init."""
    max_sum = 0  # Bug: should init to first element to handle all-negative arrays
    current = 0
    for n in nums:
        current = max(n, current + n)
        max_sum = max(max_sum, current)
    return max_sum
