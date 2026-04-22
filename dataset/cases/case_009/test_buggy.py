from buggy import safe_divide

def test_divide_normal():
    assert safe_divide(10.0, 2.0) == 5.0

def test_divide_by_zero_returns_float():
    result = safe_divide(5.0, 0)
    assert isinstance(result, float), f"Expected float, got {type(result)}"

def test_divide_by_zero_value():
    assert safe_divide(5.0, 0) == 0.0
