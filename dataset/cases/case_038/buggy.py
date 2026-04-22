def make_adders():
    adders = []
    for i in range(5):
        adders.append(lambda x: x + i)  # Bug: late binding closure — all capture same i
    return adders
