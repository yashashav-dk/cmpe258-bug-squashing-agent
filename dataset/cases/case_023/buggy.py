def is_palindrome(s: str) -> bool:
    return s == s[::-1]  # Bug: case-sensitive, fails "Racecar"
