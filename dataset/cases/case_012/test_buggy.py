from buggy import join_words

def test_join_basic():
    assert join_words(["apple", "banana", "cherry"]) == "apple, banana, cherry"

def test_join_custom_sep():
    assert join_words(["a", "b", "c"], " | ") == "a | b | c"

def test_join_single():
    assert join_words(["only"]) == "only"
