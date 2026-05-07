def absolute_value(n: int):
    if n >= 0:
        return n
    # Bug: missing `return -n` for negative branch — returns None
