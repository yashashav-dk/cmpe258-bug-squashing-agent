from buggy import add_numbers


def test_add_numbers_returns_int():
    result = add_numbers(3, 4)
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    assert result == 7


def test_add_numbers_negative():
    assert add_numbers(-1, 1) == 0
