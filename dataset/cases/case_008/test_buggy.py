from buggy import to_uppercase

def test_upper_basic():
    assert to_uppercase(["hello", "world"]) == ["HELLO", "WORLD"]

def test_upper_mixed():
    assert to_uppercase(["Python"]) == ["PYTHON"]

def test_upper_empty():
    assert to_uppercase([]) == []
