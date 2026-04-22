from buggy import word_lengths, char_frequency


def test_word_lengths_basic():
    result = word_lengths(["hi", "hello", "to", "world"])
    assert result == {"hello": 5, "world": 5}


def test_word_lengths_all_long():
    result = word_lengths(["foo", "bar", "baz"])
    assert result == {"foo": 3, "bar": 3, "baz": 3}


def test_char_frequency_basic():
    result = char_frequency("aab")
    assert result == {"a": 2, "b": 1}, f"Got: {result}"


def test_char_frequency_single():
    result = char_frequency("xyz")
    assert result == {"x": 1, "y": 1, "z": 1}, f"Got: {result}"
