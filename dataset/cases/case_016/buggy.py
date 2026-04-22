def flatten_one_level(nested: list) -> list:
    result = []
    for item in nested:
        result.append(item)  # Bug: append instead of extend — doesn't flatten
    return result
