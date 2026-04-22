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
