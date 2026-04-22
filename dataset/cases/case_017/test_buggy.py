from buggy import strip_and_split

def test_strip_split_basic():
    assert strip_and_split("  hello world  ") == ["hello", "world"]

def test_strip_split_single():
    assert strip_and_split("  one  ") == ["one"]

def test_strip_split_empty():
    assert strip_and_split("   ") == []
