def make_multiplier(factor: int):
    def multiply(x: int) -> int:
        return x * factor
    return multiply
