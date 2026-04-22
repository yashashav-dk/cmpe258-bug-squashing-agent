from buggy import count_words

def test_basic():
    assert count_words("hello world foo") == 3

def test_extra_spaces():
    assert count_words("  one   two  ") == 2

def test_empty():
    assert count_words("") == 0
