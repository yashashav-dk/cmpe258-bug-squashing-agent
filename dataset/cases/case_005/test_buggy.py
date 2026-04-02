from buggy import absolute_value


def test_positive():
    assert absolute_value(5) == 5


def test_negative():
    assert absolute_value(-3) == 3


def test_zero():
    assert absolute_value(0) == 0
