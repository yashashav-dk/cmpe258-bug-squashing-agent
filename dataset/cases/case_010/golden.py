def first_element(lst: list):
    if lst is None or len(lst) == 0:
        return -1
    return lst[0]

def count_items(lst: list) -> int:
    return len(lst)
