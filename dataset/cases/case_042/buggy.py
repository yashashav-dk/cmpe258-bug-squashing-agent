def get_evens(nums: list) -> list:
    evens = (x for x in nums if x % 2 == 0)
    _ = list(evens)  # Exhausts the generator
    return list(evens)  # Bug: generator already exhausted, returns []
