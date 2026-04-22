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
