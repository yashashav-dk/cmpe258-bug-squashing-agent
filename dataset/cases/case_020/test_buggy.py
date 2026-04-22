from buggy import product

def test_product_basic():
    assert product([2, 3, 4]) == 24

def test_product_single():
    assert product([7]) == 7

def test_product_with_one():
    assert product([1, 5, 6]) == 30
