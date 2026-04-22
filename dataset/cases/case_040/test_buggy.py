from buggy import make_counter

def test_counter_increments():
    c = make_counter()
    assert c() == 1
    assert c() == 2
    assert c() == 3

def test_independent_counters():
    a = make_counter()
    b = make_counter()
    a()
    a()
    assert b() == 1  # independent
