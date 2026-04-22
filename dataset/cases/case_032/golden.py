def rotate_list(lst: list, k: int) -> list:
    """Rotate list right by k positions."""
    n = len(lst)
    if n == 0:
        return lst
    k = k % n
    return lst[-k:] + lst[:-k]
