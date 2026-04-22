counter = 0

def increment():
    counter += 1  # Bug: UnboundLocalError — must declare global counter
    return counter
