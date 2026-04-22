def word_lengths(words: list) -> dict:
    """Return dict of word -> length, for words with length >= 3."""
    lengths = {word: len(word) for word in words}
    to_delete = [word for word in lengths if lengths[word] < 3]
    for word in to_delete:
        del lengths[word]
    return lengths


def char_frequency(text: str) -> dict:
    """Return frequency map of characters. Bug: skips counting first occurrence."""
    freq = {}
    for ch in text:
        if ch in freq:
            freq[ch] += 1
        # Bug: missing else — first occurrence never counted
    return freq
