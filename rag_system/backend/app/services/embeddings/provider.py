import hashlib
from abc import ABC, abstractmethod
from typing import List
import numpy as np
import requests


class EmbeddingProvider(ABC):
    """Abstract Base Class for Embedding Providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector embedding dimension."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate normalized embeddings for a list of document chunk texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate normalized embedding for a single user query."""
        pass


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-semantic mock embedding provider for tests and zero-API-key local development.
    Generates unit-normalized vectors derived from token hashes so that shared vocabulary
    produces realistic semantic similarity scores.
    """

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_to_vector(self, text: str) -> List[float]:
        import re
        tokens = [t.lower().strip() for t in re.findall(r"\w+", text) if len(t) >= 3]
        if not tokens:
            tokens = [text.strip()]

        combined = np.zeros(self._dim, dtype=np.float32)
        for tok in set(tokens):
            seed = int(hashlib.sha256(tok.encode("utf-8")).hexdigest()[:8], 16)
            rng = np.random.RandomState(seed)
            v = rng.randn(self._dim).astype(np.float32)
            norm = np.linalg.norm(v)
            if norm > 0:
                combined += (v / norm)

        total_norm = np.linalg.norm(combined)
        if total_norm > 0:
            combined = combined / total_norm
        return combined.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_to_vector(text)


class GoogleGeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini Embedding Provider (e.g. models/gemini-embedding-001)."""

    def __init__(self, api_key: str, model: str = "models/gemini-embedding-001"):
        if not api_key:
            raise ValueError("Google Gemini Embedding Provider requires an API key.")
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self._dim = 3072

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = []
        for t in texts:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent?key={self.api_key}"
            payload = {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t[:2000]}]}
            }
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            if response.status_code != 200:
                raise RuntimeError(f"Gemini embedding API error ({response.status_code}): {response.text}")

            vals = response.json().get("embedding", {}).get("values", [])
            self._dim = len(vals)
            vec = np.array(vals, dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec.tolist())
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_documents([text])
        return res[0] if res else [0.0] * self._dim


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding Provider (e.g. text-embedding-3-small)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not api_key:
            raise ValueError("OpenAI Embedding Provider requires an API key.")
        self.api_key = api_key
        self.model = model
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            url,
            headers=headers,
            json={"input": texts, "model": self.model},
            timeout=30
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenAI embedding API error ({response.status_code}): {response.text}")

        data = response.json()
        embeddings = []
        for item in sorted(data.get("data", []), key=lambda x: x["index"]):
            vec = np.array(item["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            embeddings.append(vec.tolist())
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        res = self.embed_documents([text])
        return res[0] if res else [0.0] * self._dim


def get_embedding_provider(
    provider_name: str,
    api_key: str = "",
    model_name: str = ""
) -> EmbeddingProvider:
    """Factory creating the appropriate EmbeddingProvider based on configuration."""
    provider = (provider_name or "mock").lower()
    if provider == "gemini":
        if not api_key:
            raise ValueError("EMBEDDING_PROVIDER is 'gemini' but EMBEDDING_API_KEY is not set.")
        return GoogleGeminiEmbeddingProvider(api_key=api_key, model=model_name or "models/text-embedding-004")
    elif provider == "openai":
        if not api_key:
            raise ValueError("EMBEDDING_PROVIDER is 'openai' but EMBEDDING_API_KEY is not set.")
        return OpenAIEmbeddingProvider(api_key=api_key, model=model_name or "text-embedding-3-small")
    elif provider in ("mock", "test"):
        return DeterministicMockEmbeddingProvider(dimension=768)
    else:
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER '{provider_name}'. Supported: gemini, openai, mock.")
