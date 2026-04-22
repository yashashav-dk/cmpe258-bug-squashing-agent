def count_occurrences(lst: list, target) -> int:
    count = 0
    for item in lst:
        if item == target:
            count += 2  # Bug: increments by 2 instead of 1
    return count
