"""BGE Reranker for improving retrieval quality."""
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid loading heavy models at startup
_reranker = None


class BGEReranker:
    """
    Reranker using BGE cross-encoder for Vietnamese text.

    Model: BAAI/bge-reranker-base (works well for multilingual including Vietnamese)

    Alternative models:
    - BAAI/bge-reranker-large (better quality, slower, 1.4GB)
    - cross-encoder/ms-marco-MiniLM-L-6-v2 (faster, English-focused)

    Note: First load will download the model (~400MB for base).
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        """Initialize BGE reranker with specified model."""
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy load the model only when needed."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading reranker model: {self.model_name}")
                self._model = CrossEncoder(self.model_name, max_length=512)
                logger.info("Reranker model loaded successfully")
            except ImportError:
                logger.warning("sentence-transformers not installed. Using fallback reranker.")
                self._model = "fallback"
            except Exception as e:
                logger.error(f"Failed to load reranker: {e}")
                self._model = "fallback"

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_n: int = 5
    ) -> Tuple[List[Dict], List[float]]:
        """
        Rerank chunks using cross-encoder.

        Args:
            query: User query
            chunks: List of dicts with 'text' key
            top_n: Number of top results to return

        Returns:
            Tuple of (reranked_chunks, scores)
        """
        if not chunks:
            return [], []

        self._load_model()

        # Fallback: return original order with dummy scores
        if self._model == "fallback":
            return chunks[:top_n], [1.0 - (i * 0.1) for i in range(min(top_n, len(chunks)))]

        try:
            import numpy as np

            # Create query-chunk pairs
            pairs = []
            for chunk in chunks:
                text = chunk.get("text", "")
                if isinstance(text, str) and text:
                    pairs.append([query, text])
                else:
                    pairs.append([query, ""])

            if not pairs:
                return [], []

            # Score pairs
            scores = self._model.predict(pairs)

            # Sort by score descending
            sorted_indices = np.argsort(scores)[::-1][:top_n]

            reranked_chunks = [chunks[i] for i in sorted_indices]
            reranked_scores = [float(scores[i]) for i in sorted_indices]

            return reranked_chunks, reranked_scores

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Fallback on error
            return chunks[:top_n], [1.0 - (i * 0.1) for i in range(min(top_n, len(chunks)))]


def get_reranker() -> BGEReranker:
    """Get or create reranker singleton."""
    global _reranker
    if _reranker is None:
        _reranker = BGEReranker()
    return _reranker


def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_n: int = 5
) -> Tuple[List[Dict], List[float]]:
    """
    Convenience function to rerank chunks.

    Args:
        query: User query
        chunks: List of dicts with 'text' key
        top_n: Number of top results

    Returns:
        Tuple of (reranked_chunks, scores)
    """
    reranker = get_reranker()
    return reranker.rerank(query, chunks, top_n)
