def safe_get(d: dict, key: str, default=None):
    try:
        return d[key]
    except KeyError:
        return default
