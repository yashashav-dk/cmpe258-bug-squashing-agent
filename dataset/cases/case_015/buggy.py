def contains_digit(s: str) -> bool:
    for ch in s:
        if ch.isdigit():
            return True
    return 1  # Bug: returns int 1 instead of bool False
