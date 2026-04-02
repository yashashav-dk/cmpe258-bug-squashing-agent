from buggy import make_multiplier


def test_multiplier_by_3():
    triple = make_multiplier(3)
    assert triple(5) == 15


def test_multiplier_by_2():
    double = make_multiplier(2)
    assert double(7) == 14


def test_multiplier_by_1():
    identity = make_multiplier(1)
    assert identity(99) == 99
