import math
from typing import List, Dict
from app.config import config

class EmbeddingService:
    def __init__(self):
        self.api_key = config.GROQ_API_KEY
        self.model = config.EMBEDDING_MODEL
        self.cache: Dict[str, List[float]] = {}

    def get_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single text string."""
        if not text or not text.strip():
            return [0.0] * 768
            
        if text in self.cache:
            return self.cache[text]
            
        embeddings = self.get_embeddings_batch([text])
        return embeddings[0]

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings for a batch of text strings, with caching and normalization."""
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache
        for idx, text in enumerate(texts):
            if text in self.cache:
                results.append(self.cache[text])
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(idx)

        if not uncached_texts:
            return results

        # Process uncached texts in batches of 16
        batch_size = 16
        for i in range(0, len(uncached_texts), batch_size):
            batch = uncached_texts[i:i + batch_size]
            indices = uncached_indices[i:i + batch_size]
            
            batch_embeddings = self._fetch_embeddings(batch)
            
            for local_idx, emb in enumerate(batch_embeddings):
                normalized_emb = self._normalize_vector(emb)
                orig_idx = indices[local_idx]
                results[orig_idx] = normalized_emb
                # Cache the result
                self.cache[batch[local_idx]] = normalized_emb

        return results

    def _fetch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Always generates mock embeddings when model is local."""
        return [self._generate_mock_vector(t) for t in texts]

    def _normalize_vector(self, v: List[float]) -> List[float]:
        """L2 normalizes a vector."""
        squared_sum = sum(x * x for x in v)
        norm = math.sqrt(squared_sum)
        if norm == 0:
            return v
        return [x / norm for x in v]

    def _generate_mock_vector(self, text: str) -> List[float]:
        """Deterministic pseudo-random vector generator based on text hash for testing/fallback."""
        h = hash(text)
        vector = []
        # text-embedding-004 has 768 dimensions
        for i in range(768):
            # standard math formula to yield a pseudo-random value between -1 and 1
            val = math.sin(h + i) * 10000
            vector.append(val - math.floor(val))
        return self._normalize_vector(vector)
