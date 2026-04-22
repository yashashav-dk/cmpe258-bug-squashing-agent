def remove_duplicates(lst: list) -> list:
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
        else:
            result.append(item)  # Bug: appends duplicate instead of unique item
    return result
