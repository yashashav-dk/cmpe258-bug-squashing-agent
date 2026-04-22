def product(nums: list) -> int:
    result = 1
    for n in nums:
        result *= n
    return result
