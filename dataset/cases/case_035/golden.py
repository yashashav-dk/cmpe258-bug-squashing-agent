def average(nums: list) -> float:
    if not nums:
        return 0.0
    return sum(nums) / len(nums)
