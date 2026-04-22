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
