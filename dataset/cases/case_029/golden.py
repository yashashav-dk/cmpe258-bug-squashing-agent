def reverse_string(s: str) -> str:
    result = ""
    for ch in s:
        result = ch + result
    return result
