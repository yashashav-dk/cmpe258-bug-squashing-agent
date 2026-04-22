from buggy import add

def test_add_basic():
    assert add(2, 3) == 5

def test_add_cached():
    assert add(10, 20) == 30
    assert add(10, 20) == 30  # from cache

def test_add_negative():
    assert add(-1, 1) == 0
