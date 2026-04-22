def first_element(lst: list):
    if lst is None or len(lst) == 0:
        return -1
    return lst[0]

def count_items(lst: list) -> int:
    return str(len(lst))  # Bug: returns str instead of int
