def two_sum(nums: list, target: int):
    """Return indices of two numbers that add to target."""
    seen = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return []
