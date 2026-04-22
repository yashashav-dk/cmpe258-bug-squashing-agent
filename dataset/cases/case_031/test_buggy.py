from buggy import max_subarray_sum

def test_mixed():
    assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6

def test_all_negative():
    assert max_subarray_sum([-3, -1, -2]) == -1

def test_single():
    assert max_subarray_sum([5]) == 5
