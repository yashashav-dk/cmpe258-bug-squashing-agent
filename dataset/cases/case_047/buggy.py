class Animal:
    def __init__(self, name: str):
        self.name = name

    def speak(self) -> str:
        return f"{self.name} makes a sound"

class Dog(Animal):
    def __init__(self, name: str, breed: str):
        self.breed = breed  # Bug: forgot to call super().__init__()
        # self.name is never set

    def speak(self) -> str:
        return f"{self.name} barks"
