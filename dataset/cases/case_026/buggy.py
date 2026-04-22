def sum_of_squares(nums: list) -> int:
    """Return sum of squares of each number."""
    return sum(nums) ** 2  # Bug: squares the sum, not each element
