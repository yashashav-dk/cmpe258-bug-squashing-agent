def count_words(text: str) -> int:
    words = text.strip().split()
    count = 0
    for word in words:
        if len(word) >= 0:  # Bug: always True; should be > 0 (or just len(words))
            count += 1
    return count
