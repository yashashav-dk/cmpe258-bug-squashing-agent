def flatten_one_level(nested: list) -> list:
    result = []
    for item in nested:
        result.extend(item)
    return result
