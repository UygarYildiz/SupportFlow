"""Deterministic offline embedder (EMBEDDING_MODE=fake, ADR-014).

Feature hashing over Turkish word stems: each word is lowercased with Turkish
rules, cut to its first five letters (so "teslimat", "teslim" and "teslimden"
meet) and hashed into one of the vector's dimensions. Texts that share words end
up close. Good enough to exercise retrieval in tests, CI and the demo for free;
it does not understand synonyms, which is what the live model is for.
"""

import hashlib
import math
import re

from app.agent.llm.fake import turkish_lower

_WORD = re.compile(r"[a-zçğıöşü0-9]+")
_STEM_LENGTH = 5
# Very common words that would otherwise pull unrelated texts together.
_STOPWORDS = frozenset([
    "ve", "ile", "bir", "bu", "da", "de", "için", "ya", "veya", "ise", "olan", "olarak",
    "gibi", "daha", "en", "çok", "her", "ne", "mi", "mı", "mu", "mü",
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "in", "on", "for",
])  # fmt: skip


class FakeEmbedder:
    def __init__(self, dimensions: int) -> None:
        self._dimensions = dimensions

    @property
    def model_name(self) -> str:
        return f"fake-embedding@{self._dimensions}"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for word in _WORD.findall(turkish_lower(text)):
            if word in _STOPWORDS or len(word) < 2:
                continue
            stem = word[:_STEM_LENGTH]
            digest = hashlib.blake2b(stem.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            # No usable words: a fixed unit vector, so the search still returns something.
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]
