def make_multiplier(factor: int):
    def multiply(factor: int) -> int:  # Bug: parameter shadows outer 'factor'
        return factor * factor          # multiplies by itself, not outer factor
    return multiply
