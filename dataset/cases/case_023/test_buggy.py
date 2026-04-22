from buggy import is_palindrome

def test_lower_palindrome():
    assert is_palindrome("racecar") is True

def test_mixed_case():
    assert is_palindrome("Racecar") is True

def test_not_palindrome():
    assert is_palindrome("hello") is False
