from buggy import sum_up_to

def test_sum_5():
    assert sum_up_to(5) == 15

def test_sum_1():
    assert sum_up_to(1) == 1

def test_sum_10():
    assert sum_up_to(10) == 55
