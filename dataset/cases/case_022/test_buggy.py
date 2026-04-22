from buggy import count_vowels

def test_lower():
    assert count_vowels("hello") == 2

def test_upper():
    assert count_vowels("ORANGE") == 3

def test_mixed():
    assert count_vowels("Python") == 1
