def word_lengths(words: list) -> dict:
    """Return dict of word -> length, for words with length >= 3."""
    return {word: len(word) for word in words if len(word) >= 3}


def char_frequency(text: str) -> dict:
    """Return frequency map of characters."""
    freq = {}
    for ch in text:
        if ch in freq:
            freq[ch] += 1
        else:
            freq[ch] = 1
    return freq
