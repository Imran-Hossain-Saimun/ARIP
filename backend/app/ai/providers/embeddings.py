"""Pluggable embedding providers (FR-088). `EMBEDDING_DIM` (1536, matching OpenAI's
text-embedding-3-small) is fixed across providers so the pgvector column never needs to
change size when swapping providers."""

import hashlib
import random
from typing import Protocol

from app.core.config import get_settings
from app.models.knowledge import EMBEDDING_DIM


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class DeterministicHashEmbeddingProvider:
    """Zero-config dev/test fallback — deterministic (same text -> same vector) but NOT
    semantically meaningful. Exercises the full pgvector storage/query pipeline without
    requiring an API key; swap in a real provider before trusting retrieval quality."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_vector(text) for text in texts]

    @staticmethod
    def _hash_vector(text: str) -> list[float]:
        rng = random.Random(hashlib.sha256(text.encode("utf-8")).digest())
        return [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [item.embedding for item in response.data]


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.openai_api_key:
        return OpenAIEmbeddingProvider(settings.openai_api_key)
    return DeterministicHashEmbeddingProvider()
