def contains_digit(s: str) -> bool:
    for ch in s:
        if ch.isdigit():
            return True
    return False
