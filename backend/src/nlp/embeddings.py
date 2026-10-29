from typing import List, Optional
import numpy as np
import torch


class EmbeddingEngine:
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    DIMENSION = 384

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or self.DEFAULT_MODEL
        if device is not None:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.DIMENSION

        vector = self.model.encode(text, normalize_embeddings=True)
        return [float(x) for x in vector]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Replace empty strings with temporary placeholder to maintain batch dimension
        processed_texts = [t if t and t.strip() else " " for t in texts]
        vectors = self.model.encode(processed_texts, normalize_embeddings=True)

        results: List[List[float]] = []
        for i, original in enumerate(texts):
            if not original or not original.strip():
                results.append([0.0] * self.DIMENSION)
            else:
                results.append([float(x) for x in vectors[i]])

        return results
