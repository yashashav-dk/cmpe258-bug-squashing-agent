from buggy import filter_positive

def test_mixed():
    assert filter_positive([1, -2, 3, -4, 5]) == [1, 3, 5]

def test_all_positive():
    assert filter_positive([1, 2, 3]) == [1, 2, 3]

def test_all_negative():
    assert filter_positive([-1, -2, -3]) == []
