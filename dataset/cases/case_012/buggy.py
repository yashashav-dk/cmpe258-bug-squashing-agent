def join_words(words: list, sep: str = ", ") -> str:
    return sep.join(words[0])  # Bug: joins chars of first word, not list of words
