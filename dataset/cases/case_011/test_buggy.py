from buggy import parse_age

def test_parse_age_basic():
    result = parse_age("25")
    assert isinstance(result, int)
    assert result == 25

def test_parse_age_with_spaces():
    assert parse_age("  30  ") == 30
