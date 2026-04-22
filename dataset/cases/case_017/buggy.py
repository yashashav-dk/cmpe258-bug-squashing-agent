def strip_and_split(text: str) -> list:
    return text.split().strip()  # Bug: list has no strip(); should strip first
