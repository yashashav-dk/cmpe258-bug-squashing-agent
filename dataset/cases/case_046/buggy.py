def safe_get(d: dict, key: str, default=None):
    try:
        return d[key]
    except TypeError:  # Bug: wrong exception — should catch KeyError
        return default
