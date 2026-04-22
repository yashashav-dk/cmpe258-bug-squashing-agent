from buggy import celsius_to_fahrenheit, celsius_to_kelvin

def test_freezing_f():
    assert celsius_to_fahrenheit(0) == 32.0

def test_boiling_f():
    assert celsius_to_fahrenheit(100) == 212.0

def test_freezing_kelvin():
    assert celsius_to_kelvin(0) == 273.15

def test_boiling_kelvin():
    assert celsius_to_kelvin(100) == 373.15
