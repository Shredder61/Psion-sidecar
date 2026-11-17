"""Replaceable word-list interface for Sidecar Scrabble.

No word list is bundled. Load a separately obtained, licensed word list with
WordDictionary.from_file(), or construct a dictionary from an iterable.
"""

from pathlib import Path


def normalise_word(word):
    """Return an uppercase A-Z word, rejecting empty or non-letter input."""
    if not isinstance(word, str):
        raise TypeError("A dictionary word must be text")
    normalised = word.strip().upper()
    if not normalised or any(letter < "A" or letter > "Z" for letter in normalised):
        raise ValueError(f"Invalid dictionary entry: {word!r}")
    return normalised


class WordDictionary:
    """In-memory exact word lookup, independent of any particular lexicon."""

    def __init__(self, words=()):
        self._words = set()
        for word in words:
            self._words.add(normalise_word(word))

    @classmethod
    def from_file(cls, filename, encoding="utf-8-sig"):
        """Load one word per line; blank lines and # comments are ignored.

        Invalid non-comment entries raise ValueError with the source line
        number. This avoids silently changing the contents of a lexicon.
        """
        words = []
        path = Path(filename)
        with path.open("r", encoding=encoding) as source:
            for line_number, line in enumerate(source, 1):
                entry = line.strip()
                if not entry or entry.startswith("#"):
                    continue
                try:
                    words.append(normalise_word(entry))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid word-list entry on line {line_number}: {entry!r}"
                    ) from exc
        return cls(words)

    def contains(self, word):
        """Return whether word is in the lexicon (case-insensitive)."""
        try:
            return normalise_word(word) in self._words
        except (TypeError, ValueError):
            return False

    def __contains__(self, word):
        return self.contains(word)

    def __len__(self):
        return len(self._words)

    def __iter__(self):
        return iter(self._words)
