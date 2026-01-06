"""Embedding service for RAG queries using SentenceTransformers.

Uses a model that produces 768-dimensional embeddings to match
the PhoBERT embeddings stored in Neo4j.

Note: The original data was embedded using PhoBERT (vinai/phobert-base).
We use a multilingual model that produces the same dimension (768).
"""
import os
import logging
from typing import List, Optional
import numpy as np

# Avoid TensorFlow/Keras issues - use PyTorch backend only
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["USE_TORCH"] = "1"

logger = logging.getLogger(__name__)

# Lazy initialization
_embedding_model = None
# Use multilingual model with 768 dimensions to match PhoBERT
_model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


def get_embedding_model():
    """Get or create SentenceTransformer model singleton."""
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {_model_name}")
            _embedding_model = SentenceTransformer(_model_name)
            logger.info("Embedding model loaded successfully")
        except ImportError:
            logger.error("sentence-transformers not installed")
            raise ImportError("sentence-transformers is required for embedding")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    return _embedding_model


def embed_query(text: str) -> List[float]:
    """
    Embed a query text using SentenceTransformer.

    Args:
        text: Query string to embed

    Returns:
        List of floats (768 dimensions for paraphrase-multilingual-mpnet-base-v2)
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    if len(text) > 10000:
        logger.warning(f"Text truncated from {len(text)} to 10000 chars")
        text = text[:10000]

    model = get_embedding_model()
    embedding = model.encode(text)

    # Convert numpy array to list for Neo4j compatibility
    if isinstance(embedding, np.ndarray):
        return embedding.tolist()
    return list(embedding)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts in batch.

    Args:
        texts: List of strings to embed

    Returns:
        List of embedding vectors
    """
    model = get_embedding_model()
    embeddings = model.encode(texts)

    return [emb.tolist() if isinstance(emb, np.ndarray) else list(emb)
            for emb in embeddings]


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings (768 for multilingual-mpnet-base-v2)."""
    return 768
