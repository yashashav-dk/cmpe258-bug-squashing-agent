import buggy

def test_increment_once():
    buggy.counter = 0
    assert buggy.increment() == 1

def test_increment_twice():
    buggy.counter = 0
    buggy.increment()
    assert buggy.increment() == 2
