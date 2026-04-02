from buggy import find_max


def test_find_max_basic():
    assert find_max([3, 1, 4, 1, 5, 9, 2]) == 9


def test_find_max_negatives():
    assert find_max([-5, -1, -3]) == -1


def test_find_max_single():
    assert find_max([42]) == 42
