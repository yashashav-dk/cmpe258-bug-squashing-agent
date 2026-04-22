from buggy import linear_search

def test_found():
    assert linear_search([10, 20, 30, 40], 30) == 2

def test_not_found():
    assert linear_search([1, 2, 3], 99) == -1

def test_first():
    assert linear_search([5, 6, 7], 5) == 0
