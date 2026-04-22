from buggy import get_config

def test_default_host():
    assert get_config("host") == "localhost"

def test_default_port():
    assert get_config("port") == "8080"

def test_override():
    assert get_config("host", {"host": "example.com"}) == "example.com"
