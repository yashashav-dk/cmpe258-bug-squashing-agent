from buggy import get_last_n


def test_get_last_n_basic():
    assert get_last_n([1, 2, 3, 4, 5], 3) == [3, 4, 5]


def test_get_last_n_one():
    assert get_last_n([10, 20, 30], 1) == [30]


def test_get_last_n_all():
    assert get_last_n([1, 2], 2) == [1, 2]
