def build_range(start: int, stop: int) -> list:
    return list(range(start, stop - 1))  # Bug: off-by-one, excludes stop-1
