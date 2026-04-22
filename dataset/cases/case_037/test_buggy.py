from buggy import append_item

def test_independent_calls():
    r1 = append_item(1)
    r2 = append_item(2)
    assert r1 == [1], f"Expected [1], got {r1}"
    assert r2 == [2], f"Expected [2], got {r2}"

def test_explicit_list():
    assert append_item(5, [10, 20]) == [10, 20, 5]
