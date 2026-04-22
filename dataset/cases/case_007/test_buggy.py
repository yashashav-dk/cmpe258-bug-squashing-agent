from buggy import repeat_str

def test_repeat_basic():
    assert repeat_str("ab", 3) == "ababab"

def test_repeat_one():
    assert repeat_str("x", 1) == "x"

def test_repeat_type():
    assert isinstance(repeat_str("hi", 2), str)
