def fibonacci(n: int) -> int:
    """Return nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1)."""
    if n <= 0:
        return 1  # Bug: fib(0) should be 0
    if n == 1:
        return 1
    return fibonacci(n - 1) + fibonacci(n - 2)
