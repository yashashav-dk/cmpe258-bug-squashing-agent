from buggy import binary_search

def test_found():
    assert binary_search([1, 3, 5, 7, 9], 7) == 3

def test_not_found():
    assert binary_search([1, 3, 5], 4) == -1

def test_first():
    assert binary_search([2, 4, 6, 8], 2) == 0
