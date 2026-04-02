def find_max(lst: list) -> int:
    max_val = lst[0]
    for x in lst:
        if x > max_val:
            max_val = x
    return max_val
