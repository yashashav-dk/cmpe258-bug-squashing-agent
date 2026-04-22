def get_config(key: str, overrides: dict = None) -> str:
    defaults = {"host": "localhost", "port": "8080", "debug": "false"}
    if overrides:
        defaults.update(overrides)
    return defaults[key]
