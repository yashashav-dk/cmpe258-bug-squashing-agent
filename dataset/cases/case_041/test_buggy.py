from buggy import Stack

def test_independent_stacks():
    s1 = Stack()
    s2 = Stack()
    s1.push(1)
    s1.push(2)
    assert s2.size() == 0, f"s2 should be empty, got size {s2.size()}"

def test_push_pop():
    s = Stack()
    s.push(10)
    s.push(20)
    assert s.pop() == 20
    assert s.size() == 1
