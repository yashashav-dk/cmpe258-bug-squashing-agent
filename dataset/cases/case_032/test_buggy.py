from buggy import rotate_list

def test_rotate_right():
    assert rotate_list([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]

def test_rotate_by_length():
    assert rotate_list([1, 2, 3], 3) == [1, 2, 3]

def test_rotate_one():
    assert rotate_list([1, 2, 3, 4], 1) == [4, 1, 2, 3]
