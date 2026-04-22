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
