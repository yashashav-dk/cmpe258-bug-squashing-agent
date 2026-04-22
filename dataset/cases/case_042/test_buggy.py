from buggy import get_evens

def test_basic():
    assert get_evens([1, 2, 3, 4, 5, 6]) == [2, 4, 6]

def test_no_evens():
    assert get_evens([1, 3, 5]) == []

def test_all_evens():
    assert get_evens([2, 4, 6]) == [2, 4, 6]
