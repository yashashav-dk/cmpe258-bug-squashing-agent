def make_multiplier(factor: int):
    def multiply(n: int) -> int:
        return factor * n
    return multiply
