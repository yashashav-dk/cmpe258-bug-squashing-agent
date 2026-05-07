def get_last_n(lst: list, n: int) -> list:
    return lst[-n + 1:]  # Bug: off-by-one, should be lst[-n:]
