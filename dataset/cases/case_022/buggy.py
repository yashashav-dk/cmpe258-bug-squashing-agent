def count_vowels(s: str) -> int:
    vowels = "aeiou"
    return sum(1 for ch in s if ch in vowels)  # Bug: no .lower(), misses uppercase
