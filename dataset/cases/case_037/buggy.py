def append_item(item, lst=[]):  # Bug: mutable default argument
    lst.append(item)
    return lst
