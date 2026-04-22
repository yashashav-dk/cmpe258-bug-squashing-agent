from buggy import merge_sorted

def test_basic():
    assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]

def test_one_empty():
    assert merge_sorted([], [1, 2, 3]) == [1, 2, 3]

def test_second_longer():
    assert merge_sorted([1, 2], [3, 4, 5]) == [1, 2, 3, 4, 5]
