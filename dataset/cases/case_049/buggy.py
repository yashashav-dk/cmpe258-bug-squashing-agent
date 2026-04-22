import functools

def memoize(fn):
    cache = {}
    @functools.wraps(fn)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = fn(args)  # Bug: passes args tuple, not unpacked
        cache[args] = result
        return result
    return wrapper

@memoize
def add(a, b):
    return a + b
