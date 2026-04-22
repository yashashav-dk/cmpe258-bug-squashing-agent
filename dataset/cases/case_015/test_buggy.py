from buggy import contains_digit

def test_has_digit():
    assert contains_digit("abc3def") is True

def test_no_digit_type():
    result = contains_digit("hello")
    assert result is False, f"Expected False, got {result!r}"

def test_empty():
    assert contains_digit("") is False
