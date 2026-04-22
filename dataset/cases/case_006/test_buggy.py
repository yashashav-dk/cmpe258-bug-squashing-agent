from buggy import divide

def test_divide_basic():
    assert divide(7, 2) == 3.5

def test_divide_exact():
    assert divide(10, 4) == 2.5

def test_divide_whole():
    assert divide(9, 3) == 3.0
