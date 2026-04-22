def make_adders():
    adders = []
    for i in range(5):
        adders.append(lambda x, n=i: x + n)
    return adders
