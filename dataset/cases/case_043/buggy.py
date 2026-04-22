def filter_positive(nums: list) -> list:
    result = []
    for n in nums:
        if n > 0:
            result.append(n)
        nums.remove(n)  # Bug: modifying list while iterating causes skipped elements
    return result
