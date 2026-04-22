def make_counter():
    count = 0
    def increment():
        count += 1  # Bug: needs nonlocal — UnboundLocalError
        return count
    return increment
