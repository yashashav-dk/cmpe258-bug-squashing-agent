from buggy import safe_get

def test_key_exists():
    assert safe_get({"a": 1}, "a") == 1

def test_key_missing_returns_default():
    assert safe_get({"a": 1}, "b") is None

def test_key_missing_custom_default():
    assert safe_get({}, "x", "fallback") == "fallback"
