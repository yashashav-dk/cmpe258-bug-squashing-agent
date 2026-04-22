def to_uppercase(words: list) -> list:
    return [w.lower() for w in words]  # Bug: lower() instead of upper()
