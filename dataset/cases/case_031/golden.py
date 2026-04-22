def max_subarray_sum(nums: list) -> int:
    """Kadane's algorithm."""
    max_sum = nums[0]
    current = nums[0]
    for n in nums[1:]:
        current = max(n, current + n)
        max_sum = max(max_sum, current)
    return max_sum
