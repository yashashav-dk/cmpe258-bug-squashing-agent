import functools

def memoize(fn):
    cache = {}
    @functools.wraps(fn)
    def wrapper(*args):
        if args in cache:
            return cache[args]
        result = fn(*args)
        cache[args] = result
        return result
    return wrapper

@memoize
def add(a, b):
    return a + b
