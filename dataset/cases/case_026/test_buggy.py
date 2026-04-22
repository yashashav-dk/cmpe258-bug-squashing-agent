from buggy import sum_of_squares

def test_basic():
    assert sum_of_squares([1, 2, 3]) == 14  # 1+4+9

def test_single():
    assert sum_of_squares([5]) == 25

def test_zeros():
    assert sum_of_squares([0, 0, 0]) == 0
