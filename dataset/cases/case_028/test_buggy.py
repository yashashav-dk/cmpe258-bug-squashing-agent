from buggy import count_occurrences

def test_multiple():
    assert count_occurrences([1, 2, 1, 3, 1], 1) == 3

def test_none():
    assert count_occurrences([1, 2, 3], 5) == 0

def test_single():
    assert count_occurrences([7, 8, 9], 7) == 1
