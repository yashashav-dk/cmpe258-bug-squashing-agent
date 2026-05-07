def celsius_to_fahrenheit(c: float) -> float:
    return c * 9 / 5 + 32  # Bug: operator precedence — actually this is correct
# Actual bug: uses wrong formula (subtracts instead of adds)
def celsius_to_kelvin(c: float) -> float:
    return c - 273.15  # Bug: should add, not subtract
