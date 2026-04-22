def linear_search(lst: list, target) -> int:
    for i, val in enumerate(lst):
        if val == target:
            return i
    return -1
