#!/usr/bin/env python3
"""
generate_cases.py — Creates all 45 remaining bug cases (006–050).
Run from project root: python3 generate_cases.py
"""
import os, textwrap

ROOT = os.path.join(os.path.dirname(__file__), "dataset", "cases")

CASES = {
    # ── TIER 1: Syntax / Type (cases 006–018) ──────────────────────────────
    "case_006": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def divide(a: int, b: int) -> float:
                return a // b  # Bug: integer division truncates; should use /
            """),
        "golden": textwrap.dedent("""\
            def divide(a: int, b: int) -> float:
                return a / b
            """),
        "tests": textwrap.dedent("""\
            from buggy import divide

            def test_divide_basic():
                assert divide(7, 2) == 3.5

            def test_divide_exact():
                assert divide(10, 4) == 2.5

            def test_divide_whole():
                assert divide(9, 3) == 3.0
            """),
    },
    "case_007": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def repeat_str(s: str, n: int) -> str:
                return [s] * n  # Bug: returns a list, not a string
            """),
        "golden": textwrap.dedent("""\
            def repeat_str(s: str, n: int) -> str:
                return s * n
            """),
        "tests": textwrap.dedent("""\
            from buggy import repeat_str

            def test_repeat_basic():
                assert repeat_str("ab", 3) == "ababab"

            def test_repeat_one():
                assert repeat_str("x", 1) == "x"

            def test_repeat_type():
                assert isinstance(repeat_str("hi", 2), str)
            """),
    },
    "case_008": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def to_uppercase(words: list) -> list:
                return [w.lower() for w in words]  # Bug: lower() instead of upper()
            """),
        "golden": textwrap.dedent("""\
            def to_uppercase(words: list) -> list:
                return [w.upper() for w in words]
            """),
        "tests": textwrap.dedent("""\
            from buggy import to_uppercase

            def test_upper_basic():
                assert to_uppercase(["hello", "world"]) == ["HELLO", "WORLD"]

            def test_upper_mixed():
                assert to_uppercase(["Python"]) == ["PYTHON"]

            def test_upper_empty():
                assert to_uppercase([]) == []
            """),
    },
    "case_009": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def safe_divide(a: float, b: float) -> float:
                if b == 0:
                    return None  # Bug: should return 0.0, not None
                return a / b
            """),
        "golden": textwrap.dedent("""\
            def safe_divide(a: float, b: float) -> float:
                if b == 0:
                    return 0.0
                return a / b
            """),
        "tests": textwrap.dedent("""\
            from buggy import safe_divide

            def test_divide_normal():
                assert safe_divide(10.0, 2.0) == 5.0

            def test_divide_by_zero_returns_float():
                result = safe_divide(5.0, 0)
                assert isinstance(result, float), f"Expected float, got {type(result)}"

            def test_divide_by_zero_value():
                assert safe_divide(5.0, 0) == 0.0
            """),
    },
    "case_010": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def first_element(lst: list):
                if lst is None or len(lst) == 0:
                    return -1
                return lst[0]

            def count_items(lst: list) -> int:
                return str(len(lst))  # Bug: returns str instead of int
            """),
        "golden": textwrap.dedent("""\
            def first_element(lst: list):
                if lst is None or len(lst) == 0:
                    return -1
                return lst[0]

            def count_items(lst: list) -> int:
                return len(lst)
            """),
        "tests": textwrap.dedent("""\
            from buggy import first_element, count_items

            def test_first_element_normal():
                assert first_element([10, 20, 30]) == 10

            def test_first_element_empty():
                assert first_element([]) == -1

            def test_count_returns_int():
                result = count_items([1, 2, 3])
                assert isinstance(result, int), f"Expected int, got {type(result)}"
                assert result == 3
            """),
    },
    "case_011": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def parse_age(age_str: str) -> int:
                return age_str.strip()  # Bug: returns str, not int
            """),
        "golden": textwrap.dedent("""\
            def parse_age(age_str: str) -> int:
                return int(age_str.strip())
            """),
        "tests": textwrap.dedent("""\
            from buggy import parse_age

            def test_parse_age_basic():
                result = parse_age("25")
                assert isinstance(result, int)
                assert result == 25

            def test_parse_age_with_spaces():
                assert parse_age("  30  ") == 30
            """),
    },
    "case_012": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def join_words(words: list, sep: str = ", ") -> str:
                return sep.join(words[0])  # Bug: joins chars of first word, not list of words
            """),
        "golden": textwrap.dedent("""\
            def join_words(words: list, sep: str = ", ") -> str:
                return sep.join(words)
            """),
        "tests": textwrap.dedent("""\
            from buggy import join_words

            def test_join_basic():
                assert join_words(["apple", "banana", "cherry"]) == "apple, banana, cherry"

            def test_join_custom_sep():
                assert join_words(["a", "b", "c"], " | ") == "a | b | c"

            def test_join_single():
                assert join_words(["only"]) == "only"
            """),
    },
    "case_013": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def clamp(value: float, lo: float, hi: float) -> float:
                if value < lo:
                    return lo
                if value > hi:
                    return hi
                return str(value)  # Bug: returns str instead of float
            """),
        "golden": textwrap.dedent("""\
            def clamp(value: float, lo: float, hi: float) -> float:
                if value < lo:
                    return lo
                if value > hi:
                    return hi
                return value
            """),
        "tests": textwrap.dedent("""\
            from buggy import clamp

            def test_clamp_below():
                assert clamp(1.0, 5.0, 10.0) == 5.0

            def test_clamp_above():
                assert clamp(15.0, 5.0, 10.0) == 10.0

            def test_clamp_within_type():
                result = clamp(7.0, 5.0, 10.0)
                assert isinstance(result, float), f"Expected float, got {type(result)}"
                assert result == 7.0
            """),
    },
    "case_014": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def celsius_to_fahrenheit(c: float) -> float:
                return c * 9 / 5 + 32  # Bug: operator precedence — actually this is correct
            # Actual bug: uses wrong formula (subtracts instead of adds)
            def celsius_to_kelvin(c: float) -> float:
                return c - 273.15  # Bug: should add, not subtract
            """),
        "golden": textwrap.dedent("""\
            def celsius_to_fahrenheit(c: float) -> float:
                return c * 9 / 5 + 32

            def celsius_to_kelvin(c: float) -> float:
                return c + 273.15
            """),
        "tests": textwrap.dedent("""\
            from buggy import celsius_to_fahrenheit, celsius_to_kelvin

            def test_freezing_f():
                assert celsius_to_fahrenheit(0) == 32.0

            def test_boiling_f():
                assert celsius_to_fahrenheit(100) == 212.0

            def test_freezing_kelvin():
                assert celsius_to_kelvin(0) == 273.15

            def test_boiling_kelvin():
                assert celsius_to_kelvin(100) == 373.15
            """),
    },
    "case_015": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def contains_digit(s: str) -> bool:
                for ch in s:
                    if ch.isdigit():
                        return True
                return 1  # Bug: returns int 1 instead of bool False
            """),
        "golden": textwrap.dedent("""\
            def contains_digit(s: str) -> bool:
                for ch in s:
                    if ch.isdigit():
                        return True
                return False
            """),
        "tests": textwrap.dedent("""\
            from buggy import contains_digit

            def test_has_digit():
                assert contains_digit("abc3def") is True

            def test_no_digit_type():
                result = contains_digit("hello")
                assert result is False, f"Expected False, got {result!r}"

            def test_empty():
                assert contains_digit("") is False
            """),
    },
    "case_016": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def flatten_one_level(nested: list) -> list:
                result = []
                for item in nested:
                    result.append(item)  # Bug: append instead of extend — doesn't flatten
                return result
            """),
        "golden": textwrap.dedent("""\
            def flatten_one_level(nested: list) -> list:
                result = []
                for item in nested:
                    result.extend(item)
                return result
            """),
        "tests": textwrap.dedent("""\
            from buggy import flatten_one_level

            def test_flatten_basic():
                assert flatten_one_level([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]

            def test_flatten_strings():
                assert flatten_one_level([["a", "b"], ["c"]]) == ["a", "b", "c"]

            def test_flatten_empty():
                assert flatten_one_level([]) == []
            """),
    },
    "case_017": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def strip_and_split(text: str) -> list:
                return text.split().strip()  # Bug: list has no strip(); should strip first
            """),
        "golden": textwrap.dedent("""\
            def strip_and_split(text: str) -> list:
                return text.strip().split()
            """),
        "tests": textwrap.dedent("""\
            from buggy import strip_and_split

            def test_strip_split_basic():
                assert strip_and_split("  hello world  ") == ["hello", "world"]

            def test_strip_split_single():
                assert strip_and_split("  one  ") == ["one"]

            def test_strip_split_empty():
                assert strip_and_split("   ") == []
            """),
    },
    "case_018": {
        "tier": 1,
        "buggy": textwrap.dedent("""\
            def build_range(start: int, stop: int) -> list:
                return list(range(start, stop - 1))  # Bug: off-by-one, excludes stop-1
            """),
        "golden": textwrap.dedent("""\
            def build_range(start: int, stop: int) -> list:
                return list(range(start, stop))
            """),
        "tests": textwrap.dedent("""\
            from buggy import build_range

            def test_range_basic():
                assert build_range(1, 5) == [1, 2, 3, 4]

            def test_range_single():
                assert build_range(3, 4) == [3]

            def test_range_from_zero():
                assert build_range(0, 3) == [0, 1, 2]
            """),
    },

    # ── TIER 2: Logic / Algorithmic (cases 019–036) ─────────────────────────
    "case_019": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def sum_up_to(n: int) -> int:
                \"\"\"Return sum of integers 1..n inclusive.\"\"\"
                total = 0
                for i in range(1, n):  # Bug: should be range(1, n+1)
                    total += i
                return total
            """),
        "golden": textwrap.dedent("""\
            def sum_up_to(n: int) -> int:
                total = 0
                for i in range(1, n + 1):
                    total += i
                return total
            """),
        "tests": textwrap.dedent("""\
            from buggy import sum_up_to

            def test_sum_5():
                assert sum_up_to(5) == 15

            def test_sum_1():
                assert sum_up_to(1) == 1

            def test_sum_10():
                assert sum_up_to(10) == 55
            """),
    },
    "case_020": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def product(nums: list) -> int:
                result = 0  # Bug: should initialize to 1, not 0
                for n in nums:
                    result *= n
                return result
            """),
        "golden": textwrap.dedent("""\
            def product(nums: list) -> int:
                result = 1
                for n in nums:
                    result *= n
                return result
            """),
        "tests": textwrap.dedent("""\
            from buggy import product

            def test_product_basic():
                assert product([2, 3, 4]) == 24

            def test_product_single():
                assert product([7]) == 7

            def test_product_with_one():
                assert product([1, 5, 6]) == 30
            """),
    },
    "case_021": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def fibonacci(n: int) -> int:
                \"\"\"Return nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1).\"\"\"
                if n <= 0:
                    return 1  # Bug: fib(0) should be 0
                if n == 1:
                    return 1
                return fibonacci(n - 1) + fibonacci(n - 2)
            """),
        "golden": textwrap.dedent("""\
            def fibonacci(n: int) -> int:
                if n == 0:
                    return 0
                if n == 1:
                    return 1
                return fibonacci(n - 1) + fibonacci(n - 2)
            """),
        "tests": textwrap.dedent("""\
            from buggy import fibonacci

            def test_fib_0():
                assert fibonacci(0) == 0

            def test_fib_1():
                assert fibonacci(1) == 1

            def test_fib_7():
                assert fibonacci(7) == 13
            """),
    },
    "case_022": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def count_vowels(s: str) -> int:
                vowels = \"aeiou\"
                return sum(1 for ch in s if ch in vowels)  # Bug: no .lower(), misses uppercase
            """),
        "golden": textwrap.dedent("""\
            def count_vowels(s: str) -> int:
                vowels = \"aeiouAEIOU\"
                return sum(1 for ch in s if ch in vowels)
            """),
        "tests": textwrap.dedent("""\
            from buggy import count_vowels

            def test_lower():
                assert count_vowels("hello") == 2

            def test_upper():
                assert count_vowels("ORANGE") == 3

            def test_mixed():
                assert count_vowels("Python") == 1
            """),
    },
    "case_023": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def is_palindrome(s: str) -> bool:
                return s == s[::-1]  # Bug: case-sensitive, fails "Racecar"
            """),
        "golden": textwrap.dedent("""\
            def is_palindrome(s: str) -> bool:
                s = s.lower()
                return s == s[::-1]
            """),
        "tests": textwrap.dedent("""\
            from buggy import is_palindrome

            def test_lower_palindrome():
                assert is_palindrome("racecar") is True

            def test_mixed_case():
                assert is_palindrome("Racecar") is True

            def test_not_palindrome():
                assert is_palindrome("hello") is False
            """),
    },
    "case_024": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def is_even(n: int) -> bool:
                return n % 2 == 1  # Bug: checks odd, not even
            """),
        "golden": textwrap.dedent("""\
            def is_even(n: int) -> bool:
                return n % 2 == 0
            """),
        "tests": textwrap.dedent("""\
            from buggy import is_even

            def test_even_number():
                assert is_even(4) is True

            def test_odd_number():
                assert is_even(3) is False

            def test_zero():
                assert is_even(0) is True
            """),
    },
    "case_025": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def remove_duplicates(lst: list) -> list:
                seen = set()
                result = []
                for item in lst:
                    if item not in seen:
                        seen.add(item)
                    else:
                        result.append(item)  # Bug: appends duplicate instead of unique item
                return result
            """),
        "golden": textwrap.dedent("""\
            def remove_duplicates(lst: list) -> list:
                seen = set()
                result = []
                for item in lst:
                    if item not in seen:
                        seen.add(item)
                        result.append(item)
                return result
            """),
        "tests": textwrap.dedent("""\
            from buggy import remove_duplicates

            def test_remove_dups():
                assert remove_duplicates([1, 2, 2, 3, 1]) == [1, 2, 3]

            def test_no_dups():
                assert remove_duplicates([1, 2, 3]) == [1, 2, 3]

            def test_all_same():
                assert remove_duplicates([5, 5, 5]) == [5]
            """),
    },
    "case_026": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def sum_of_squares(nums: list) -> int:
                \"\"\"Return sum of squares of each number.\"\"\"
                return sum(nums) ** 2  # Bug: squares the sum, not each element
            """),
        "golden": textwrap.dedent("""\
            def sum_of_squares(nums: list) -> int:
                return sum(x ** 2 for x in nums)
            """),
        "tests": textwrap.dedent("""\
            from buggy import sum_of_squares

            def test_basic():
                assert sum_of_squares([1, 2, 3]) == 14  # 1+4+9

            def test_single():
                assert sum_of_squares([5]) == 25

            def test_zeros():
                assert sum_of_squares([0, 0, 0]) == 0
            """),
    },
    "case_027": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def linear_search(lst: list, target) -> int:
                \"\"\"Return index of target, or -1 if not found.\"\"\"
                for i, val in enumerate(lst):
                    if val == target:
                        return i
                return 0  # Bug: should return -1 when not found
            """),
        "golden": textwrap.dedent("""\
            def linear_search(lst: list, target) -> int:
                for i, val in enumerate(lst):
                    if val == target:
                        return i
                return -1
            """),
        "tests": textwrap.dedent("""\
            from buggy import linear_search

            def test_found():
                assert linear_search([10, 20, 30, 40], 30) == 2

            def test_not_found():
                assert linear_search([1, 2, 3], 99) == -1

            def test_first():
                assert linear_search([5, 6, 7], 5) == 0
            """),
    },
    "case_028": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def count_occurrences(lst: list, target) -> int:
                count = 0
                for item in lst:
                    if item == target:
                        count += 2  # Bug: increments by 2 instead of 1
                return count
            """),
        "golden": textwrap.dedent("""\
            def count_occurrences(lst: list, target) -> int:
                count = 0
                for item in lst:
                    if item == target:
                        count += 1
                return count
            """),
        "tests": textwrap.dedent("""\
            from buggy import count_occurrences

            def test_multiple():
                assert count_occurrences([1, 2, 1, 3, 1], 1) == 3

            def test_none():
                assert count_occurrences([1, 2, 3], 5) == 0

            def test_single():
                assert count_occurrences([7, 8, 9], 7) == 1
            """),
    },
    "case_029": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def reverse_string(s: str) -> str:
                result = \"\"
                for ch in s:
                    result = result + ch  # Bug: appends forward, doesn't reverse
                return result
            """),
        "golden": textwrap.dedent("""\
            def reverse_string(s: str) -> str:
                result = \"\"
                for ch in s:
                    result = ch + result
                return result
            """),
        "tests": textwrap.dedent("""\
            from buggy import reverse_string

            def test_basic():
                assert reverse_string("hello") == "olleh"

            def test_palindrome():
                assert reverse_string("abba") == "abba"

            def test_single():
                assert reverse_string("a") == "a"
            """),
    },
    "case_030": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def two_sum(nums: list, target: int):
                \"\"\"Return indices of two numbers that add to target.\"\"\"\
                seen = {}
                for i, num in enumerate(nums):
                    complement = target + num  # Bug: should be target - num
                    if complement in seen:
                        return [seen[complement], i]
                    seen[num] = i
                return []
            """),
        "golden": textwrap.dedent("""\
            def two_sum(nums: list, target: int):
                seen = {}
                for i, num in enumerate(nums):
                    complement = target - num
                    if complement in seen:
                        return [seen[complement], i]
                    seen[num] = i
                return []
            """),
        "tests": textwrap.dedent("""\
            from buggy import two_sum

            def test_basic():
                assert two_sum([2, 7, 11, 15], 9) == [0, 1]

            def test_middle():
                assert two_sum([3, 2, 4], 6) == [1, 2]

            def test_not_found():
                assert two_sum([1, 2, 3], 100) == []
            """),
    },
    "case_031": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def max_subarray_sum(nums: list) -> int:
                \"\"\"Kadane's algorithm. Bug: wrong init.\"\"\"\
                max_sum = 0  # Bug: should init to first element to handle all-negative arrays
                current = 0
                for n in nums:
                    current = max(n, current + n)
                    max_sum = max(max_sum, current)
                return max_sum
            """),
        "golden": textwrap.dedent("""\
            def max_subarray_sum(nums: list) -> int:
                max_sum = nums[0]
                current = nums[0]
                for n in nums[1:]:
                    current = max(n, current + n)
                    max_sum = max(max_sum, current)
                return max_sum
            """),
        "tests": textwrap.dedent("""\
            from buggy import max_subarray_sum

            def test_mixed():
                assert max_subarray_sum([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6

            def test_all_negative():
                assert max_subarray_sum([-3, -1, -2]) == -1

            def test_single():
                assert max_subarray_sum([5]) == 5
            """),
    },
    "case_032": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def rotate_list(lst: list, k: int) -> list:
                \"\"\"Rotate list right by k positions.\"\"\"\
                n = len(lst)
                if n == 0:
                    return lst
                k = k % n
                return lst[k:] + lst[:k]  # Bug: rotates left, not right
            """),
        "golden": textwrap.dedent("""\
            def rotate_list(lst: list, k: int) -> list:
                n = len(lst)
                if n == 0:
                    return lst
                k = k % n
                return lst[-k:] + lst[:-k]
            """),
        "tests": textwrap.dedent("""\
            from buggy import rotate_list

            def test_rotate_right():
                assert rotate_list([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]

            def test_rotate_by_length():
                assert rotate_list([1, 2, 3], 3) == [1, 2, 3]

            def test_rotate_one():
                assert rotate_list([1, 2, 3, 4], 1) == [4, 1, 2, 3]
            """),
    },
    "case_033": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def merge_sorted(a: list, b: list) -> list:
                result = []
                i = j = 0
                while i < len(a) and j < len(b):
                    if a[i] < b[j]:
                        result.append(a[i])
                        i += 1
                    else:
                        result.append(b[j])
                        j += 1
                result.extend(a[i:])
                result.extend(a[j:])  # Bug: should be b[j:], not a[j:]
                return result
            """),
        "golden": textwrap.dedent("""\
            def merge_sorted(a: list, b: list) -> list:
                result = []
                i = j = 0
                while i < len(a) and j < len(b):
                    if a[i] < b[j]:
                        result.append(a[i])
                        i += 1
                    else:
                        result.append(b[j])
                        j += 1
                result.extend(a[i:])
                result.extend(b[j:])
                return result
            """),
        "tests": textwrap.dedent("""\
            from buggy import merge_sorted

            def test_basic():
                assert merge_sorted([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]

            def test_one_empty():
                assert merge_sorted([], [1, 2, 3]) == [1, 2, 3]

            def test_second_longer():
                assert merge_sorted([1, 2], [3, 4, 5]) == [1, 2, 3, 4, 5]
            """),
    },
    "case_034": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def binary_search(arr: list, target: int) -> int:
                lo, hi = 0, len(arr) - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        lo = mid  # Bug: should be mid + 1 (infinite loop for certain inputs)
                    else:
                        hi = mid - 1
                return -1
            """),
        "golden": textwrap.dedent("""\
            def binary_search(arr: list, target: int) -> int:
                lo, hi = 0, len(arr) - 1
                while lo <= hi:
                    mid = (lo + hi) // 2
                    if arr[mid] == target:
                        return mid
                    elif arr[mid] < target:
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return -1
            """),
        "tests": textwrap.dedent("""\
            from buggy import binary_search

            def test_found():
                assert binary_search([1, 3, 5, 7, 9], 7) == 3

            def test_not_found():
                assert binary_search([1, 3, 5], 4) == -1

            def test_first():
                assert binary_search([2, 4, 6, 8], 2) == 0
            """),
    },
    "case_035": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def average(nums: list) -> float:
                if not nums:
                    return 0.0
                return sum(nums) / len(nums) - 1  # Bug: subtracts 1 from the result
            """),
        "golden": textwrap.dedent("""\
            def average(nums: list) -> float:
                if not nums:
                    return 0.0
                return sum(nums) / len(nums)
            """),
        "tests": textwrap.dedent("""\
            from buggy import average

            def test_basic():
                assert average([1, 2, 3, 4, 5]) == 3.0

            def test_single():
                assert average([10]) == 10.0

            def test_empty():
                assert average([]) == 0.0
            """),
    },
    "case_036": {
        "tier": 2,
        "buggy": textwrap.dedent("""\
            def count_words(text: str) -> int:
                words = text.strip().split()
                count = 0
                for word in words:
                    if len(word) >= 0:  # Bug: always True; should be > 0 (or just len(words))
                        count += 1
                return count
            """),
        "golden": textwrap.dedent("""\
            def count_words(text: str) -> int:
                return len(text.strip().split())
            """),
        "tests": textwrap.dedent("""\
            from buggy import count_words

            def test_basic():
                assert count_words("hello world foo") == 3

            def test_extra_spaces():
                assert count_words("  one   two  ") == 2

            def test_empty():
                assert count_words("") == 0
            """),
    },

    # ── TIER 3: Contextual / Scope (cases 037–050) ──────────────────────────
    "case_037": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def append_item(item, lst=[]):  # Bug: mutable default argument
                lst.append(item)
                return lst
            """),
        "golden": textwrap.dedent("""\
            def append_item(item, lst=None):
                if lst is None:
                    lst = []
                lst.append(item)
                return lst
            """),
        "tests": textwrap.dedent("""\
            from buggy import append_item

            def test_independent_calls():
                r1 = append_item(1)
                r2 = append_item(2)
                assert r1 == [1], f"Expected [1], got {r1}"
                assert r2 == [2], f"Expected [2], got {r2}"

            def test_explicit_list():
                assert append_item(5, [10, 20]) == [10, 20, 5]
            """),
    },
    "case_038": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def make_adders():
                adders = []
                for i in range(5):
                    adders.append(lambda x: x + i)  # Bug: late binding closure — all capture same i
                return adders
            """),
        "golden": textwrap.dedent("""\
            def make_adders():
                adders = []
                for i in range(5):
                    adders.append(lambda x, n=i: x + n)
                return adders
            """),
        "tests": textwrap.dedent("""\
            from buggy import make_adders

            def test_adder_zero():
                adders = make_adders()
                assert adders[0](10) == 10  # add 0

            def test_adder_two():
                adders = make_adders()
                assert adders[2](10) == 12  # add 2

            def test_adder_four():
                adders = make_adders()
                assert adders[4](10) == 14  # add 4
            """),
    },
    "case_039": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            counter = 0

            def increment():
                counter += 1  # Bug: UnboundLocalError — must declare global counter
                return counter
            """),
        "golden": textwrap.dedent("""\
            counter = 0

            def increment():
                global counter
                counter += 1
                return counter
            """),
        "tests": textwrap.dedent("""\
            import buggy

            def test_increment_once():
                buggy.counter = 0
                assert buggy.increment() == 1

            def test_increment_twice():
                buggy.counter = 0
                buggy.increment()
                assert buggy.increment() == 2
            """),
    },
    "case_040": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def make_counter():
                count = 0
                def increment():
                    count += 1  # Bug: needs nonlocal — UnboundLocalError
                    return count
                return increment
            """),
        "golden": textwrap.dedent("""\
            def make_counter():
                count = 0
                def increment():
                    nonlocal count
                    count += 1
                    return count
                return increment
            """),
        "tests": textwrap.dedent("""\
            from buggy import make_counter

            def test_counter_increments():
                c = make_counter()
                assert c() == 1
                assert c() == 2
                assert c() == 3

            def test_independent_counters():
                a = make_counter()
                b = make_counter()
                a()
                a()
                assert b() == 1  # independent
            """),
    },
    "case_041": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            class Stack:
                items = []  # Bug: class variable shared across all instances

                def push(self, item):
                    self.items.append(item)

                def pop(self):
                    return self.items.pop()

                def size(self):
                    return len(self.items)
            """),
        "golden": textwrap.dedent("""\
            class Stack:
                def __init__(self):
                    self.items = []

                def push(self, item):
                    self.items.append(item)

                def pop(self):
                    return self.items.pop()

                def size(self):
                    return len(self.items)
            """),
        "tests": textwrap.dedent("""\
            from buggy import Stack

            def test_independent_stacks():
                s1 = Stack()
                s2 = Stack()
                s1.push(1)
                s1.push(2)
                assert s2.size() == 0, f"s2 should be empty, got size {s2.size()}"

            def test_push_pop():
                s = Stack()
                s.push(10)
                s.push(20)
                assert s.pop() == 20
                assert s.size() == 1
            """),
    },
    "case_042": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def get_evens(nums: list) -> list:
                evens = (x for x in nums if x % 2 == 0)
                _ = list(evens)  # Exhausts the generator
                return list(evens)  # Bug: generator already exhausted, returns []
            """),
        "golden": textwrap.dedent("""\
            def get_evens(nums: list) -> list:
                evens = [x for x in nums if x % 2 == 0]
                return evens
            """),
        "tests": textwrap.dedent("""\
            from buggy import get_evens

            def test_basic():
                assert get_evens([1, 2, 3, 4, 5, 6]) == [2, 4, 6]

            def test_no_evens():
                assert get_evens([1, 3, 5]) == []

            def test_all_evens():
                assert get_evens([2, 4, 6]) == [2, 4, 6]
            """),
    },
    "case_043": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def filter_positive(nums: list) -> list:
                result = []
                for n in nums:
                    if n > 0:
                        result.append(n)
                    nums.remove(n)  # Bug: modifying list while iterating causes skipped elements
                return result
            """),
        "golden": textwrap.dedent("""\
            def filter_positive(nums: list) -> list:
                return [n for n in nums if n > 0]
            """),
        "tests": textwrap.dedent("""\
            from buggy import filter_positive

            def test_mixed():
                assert filter_positive([1, -2, 3, -4, 5]) == [1, 3, 5]

            def test_all_positive():
                assert filter_positive([1, 2, 3]) == [1, 2, 3]

            def test_all_negative():
                assert filter_positive([-1, -2, -3]) == []
            """),
    },
    "case_044": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def word_lengths(words):
                lengths = {}
                for word in words:
                    lengths[word] = len(word)
                for word in words:  # Bug: iterating while implicitly using same dict causes issues
                    if lengths[word] < 3:
                        del lengths[word]  # Bug: RuntimeError: dictionary changed size during iteration
                return lengths
            """),
        "golden": textwrap.dedent("""\
            def word_lengths(words):
                lengths = {word: len(word) for word in words}
                return {word: length for word, length in lengths.items() if length >= 3}
            """),
        "tests": textwrap.dedent("""\
            from buggy import word_lengths

            def test_basic():
                result = word_lengths(["hi", "hello", "to", "world"])
                assert result == {"hello": 5, "world": 5}

            def test_all_long():
                result = word_lengths(["foo", "bar", "baz"])
                assert result == {"foo": 3, "bar": 3, "baz": 3}
            """),
    },
    "case_045": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            class BankAccount:
                def __init__(self, balance: float):
                    self.balance = balance

                def deposit(self, amount: float):
                    self.balance += amount

                def withdraw(self, amount: float) -> bool:
                    if amount > self.balance:
                        return False
                    self.balance -= amount
                    return True

                def get_balance(account):  # Bug: missing self — uses 'account' instead
                    return account.balance
            """),
        "golden": textwrap.dedent("""\
            class BankAccount:
                def __init__(self, balance: float):
                    self.balance = balance

                def deposit(self, amount: float):
                    self.balance += amount

                def withdraw(self, amount: float) -> bool:
                    if amount > self.balance:
                        return False
                    self.balance -= amount
                    return True

                def get_balance(self) -> float:
                    return self.balance
            """),
        "tests": textwrap.dedent("""\
            from buggy import BankAccount

            def test_deposit():
                acc = BankAccount(100.0)
                acc.deposit(50.0)
                assert acc.get_balance() == 150.0

            def test_withdraw_success():
                acc = BankAccount(200.0)
                assert acc.withdraw(50.0) is True
                assert acc.get_balance() == 150.0

            def test_withdraw_insufficient():
                acc = BankAccount(50.0)
                assert acc.withdraw(100.0) is False
                assert acc.get_balance() == 50.0
            """),
    },
    "case_046": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def safe_get(d: dict, key: str, default=None):
                try:
                    return d[key]
                except TypeError:  # Bug: wrong exception — should catch KeyError
                    return default
            """),
        "golden": textwrap.dedent("""\
            def safe_get(d: dict, key: str, default=None):
                try:
                    return d[key]
                except KeyError:
                    return default
            """),
        "tests": textwrap.dedent("""\
            from buggy import safe_get

            def test_key_exists():
                assert safe_get({"a": 1}, "a") == 1

            def test_key_missing_returns_default():
                assert safe_get({"a": 1}, "b") is None

            def test_key_missing_custom_default():
                assert safe_get({}, "x", "fallback") == "fallback"
            """),
    },
    "case_047": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            class Animal:
                def __init__(self, name: str):
                    self.name = name

                def speak(self) -> str:
                    return f\"{self.name} makes a sound\"

            class Dog(Animal):
                def __init__(self, name: str, breed: str):
                    self.breed = breed  # Bug: forgot to call super().__init__()
                    # self.name is never set

                def speak(self) -> str:
                    return f\"{self.name} barks\"
            """),
        "golden": textwrap.dedent("""\
            class Animal:
                def __init__(self, name: str):
                    self.name = name

                def speak(self) -> str:
                    return f\"{self.name} makes a sound\"

            class Dog(Animal):
                def __init__(self, name: str, breed: str):
                    super().__init__(name)
                    self.breed = breed

                def speak(self) -> str:
                    return f\"{self.name} barks\"
            """),
        "tests": textwrap.dedent("""\
            from buggy import Dog

            def test_dog_speak():
                d = Dog("Rex", "Labrador")
                assert d.speak() == "Rex barks"

            def test_dog_name():
                d = Dog("Buddy", "Poodle")
                assert d.name == "Buddy"

            def test_dog_breed():
                d = Dog("Max", "Beagle")
                assert d.breed == "Beagle"
            """),
    },
    "case_048": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def get_config(key: str, overrides: dict = None) -> str:
                defaults = {\"host\": \"localhost\", \"port\": \"8080\", \"debug\": \"false\"}
                if overrides:
                    defaults.update(overrides)
                    return defaults[key]
                # Bug: missing return when no overrides — returns None
            """),
        "golden": textwrap.dedent("""\
            def get_config(key: str, overrides: dict = None) -> str:
                defaults = {\"host\": \"localhost\", \"port\": \"8080\", \"debug\": \"false\"}
                if overrides:
                    defaults.update(overrides)
                return defaults[key]
            """),
        "tests": textwrap.dedent("""\
            from buggy import get_config

            def test_default_host():
                assert get_config("host") == "localhost"

            def test_default_port():
                assert get_config("port") == "8080"

            def test_override():
                assert get_config("host", {"host": "example.com"}) == "example.com"
            """),
    },
    "case_049": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
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
            """),
        "golden": textwrap.dedent("""\
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
            """),
        "tests": textwrap.dedent("""\
            from buggy import add

            def test_add_basic():
                assert add(2, 3) == 5

            def test_add_cached():
                assert add(10, 20) == 30
                assert add(10, 20) == 30  # from cache

            def test_add_negative():
                assert add(-1, 1) == 0
            """),
    },
    "case_050": {
        "tier": 3,
        "buggy": textwrap.dedent("""\
            def apply_discount(price: float, discount_pct: float) -> float:
                \"\"\"Apply a percentage discount (0-100) to a price.\"\"\"\
                if not (0 <= discount_pct <= 100):
                    raise ValueError(\"Discount must be 0-100\")
                discount = price * discount_pct / 100
                return price + discount  # Bug: should subtract, not add
            """),
        "golden": textwrap.dedent("""\
            def apply_discount(price: float, discount_pct: float) -> float:
                if not (0 <= discount_pct <= 100):
                    raise ValueError(\"Discount must be 0-100\")
                discount = price * discount_pct / 100
                return price - discount
            """),
        "tests": textwrap.dedent("""\
            from buggy import apply_discount

            def test_ten_percent():
                assert apply_discount(100.0, 10) == 90.0

            def test_fifty_percent():
                assert apply_discount(200.0, 50) == 100.0

            def test_zero_discount():
                assert apply_discount(50.0, 0) == 50.0

            def test_invalid():
                import pytest
                with pytest.raises(ValueError):
                    apply_discount(100.0, 110)
            """),
    },
}


def write_case(case_id: str, data: dict):
    case_dir = os.path.join(ROOT, case_id)
    os.makedirs(case_dir, exist_ok=True)

    with open(os.path.join(case_dir, "buggy.py"), "w") as f:
        f.write(data["buggy"])
    with open(os.path.join(case_dir, "golden.py"), "w") as f:
        f.write(data["golden"])
    with open(os.path.join(case_dir, "test_buggy.py"), "w") as f:
        f.write(data["tests"])

    print(f"  ✓ {case_id}  (tier {data['tier']})")


if __name__ == "__main__":
    print(f"Writing {len(CASES)} cases to {ROOT}/ ...")
    for case_id, data in sorted(CASES.items()):
        write_case(case_id, data)
    print(f"\nDone. {len(CASES)} cases written.")
