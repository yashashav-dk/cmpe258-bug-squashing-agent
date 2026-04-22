def reverse_string(s: str) -> str:
    result = ""
    for ch in s:
        result = result + ch  # Bug: appends forward, doesn't reverse
    return result
