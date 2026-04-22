from buggy import average

def test_basic():
    assert average([1, 2, 3, 4, 5]) == 3.0

def test_single():
    assert average([10]) == 10.0

def test_empty():
    assert average([]) == 0.0
