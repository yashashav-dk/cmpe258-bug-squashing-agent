from buggy import flatten_one_level

def test_flatten_basic():
    assert flatten_one_level([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

def test_flatten_strings():
    assert flatten_one_level([["a", "b"], ["c"]]) == ["a", "b", "c"]

def test_flatten_empty():
    assert flatten_one_level([]) == []
