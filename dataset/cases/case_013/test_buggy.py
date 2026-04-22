from buggy import clamp

def test_clamp_below():
    assert clamp(1.0, 5.0, 10.0) == 5.0

def test_clamp_above():
    assert clamp(15.0, 5.0, 10.0) == 10.0

def test_clamp_within_type():
    result = clamp(7.0, 5.0, 10.0)
    assert isinstance(result, float), f"Expected float, got {type(result)}"
    assert result == 7.0
