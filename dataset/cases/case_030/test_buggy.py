from buggy import two_sum

def test_basic():
    assert two_sum([2, 7, 11, 15], 9) == [0, 1]

def test_middle():
    assert two_sum([3, 2, 4], 6) == [1, 2]

def test_not_found():
    assert two_sum([1, 2, 3], 100) == []
