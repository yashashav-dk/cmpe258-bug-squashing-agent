def parse_age(age_str: str) -> int:
    return age_str.strip()  # Bug: returns str, not int
