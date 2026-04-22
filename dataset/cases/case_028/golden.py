def count_occurrences(lst: list, target) -> int:
    count = 0
    for item in lst:
        if item == target:
            count += 1
    return count
