"""Centralized configuration for API."""
import os


class Config:
    """RAG and API configuration."""

    # RAG Pipeline
    RAG_TOP_K: int = 20
    RAG_RERANK_TOP_N: int = 5
    DEFAULT_NAMESPACE: str = os.getenv("RAG_NAMESPACE", "Test_rel_2")
    STREAM_CHUNK_SIZE: int = 100

    # JWT Auth
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


config = Config()
