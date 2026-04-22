from buggy import apply_discount

def test_ten_percent():
    assert apply_discount(100.0, 10) == 90.0

def test_fifty_percent():
    assert apply_discount(200.0, 50) == 100.0

def test_zero_discount():
    assert apply_discount(50.0, 0) == 50.0

def test_invalid():
    import pytest
    with pytest.raises(ValueError):
        apply_discount(100.0, 110)
