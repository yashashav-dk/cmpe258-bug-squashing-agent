def product(nums: list) -> int:
    result = 0  # Bug: should initialize to 1, not 0
    for n in nums:
        result *= n
    return result
