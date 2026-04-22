from buggy import build_range

def test_range_basic():
    assert build_range(1, 5) == [1, 2, 3, 4]

def test_range_single():
    assert build_range(3, 4) == [3]

def test_range_from_zero():
    assert build_range(0, 3) == [0, 1, 2]
