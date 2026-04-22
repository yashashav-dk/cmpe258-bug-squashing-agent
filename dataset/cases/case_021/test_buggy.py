from buggy import fibonacci

def test_fib_0():
    assert fibonacci(0) == 0

def test_fib_1():
    assert fibonacci(1) == 1

def test_fib_7():
    assert fibonacci(7) == 13
