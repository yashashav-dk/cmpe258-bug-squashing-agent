from buggy import first_element, count_items

def test_first_element_normal():
    assert first_element([10, 20, 30]) == 10

def test_first_element_empty():
    assert first_element([]) == -1

def test_count_returns_int():
    result = count_items([1, 2, 3])
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    assert result == 3
