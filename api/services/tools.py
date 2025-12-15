"""Tool definitions for RAG agent with Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

from api.db.neo4j import get_neo4j_client


class ToolName(str, Enum):
    """Available tool names."""
    RETRIEVE = "retrieve_from_database"
    RERANK = "rerank_results"
    GENERATE = "generate_answer"


class RetrieveInput(BaseModel):
    """Input schema for retrieve_from_database tool."""
    prompt: str = Field(..., description="User query text")
    top_k: int = Field(10, description="Number of results to retrieve")
    namespace: str = Field("Test_rel_2", description="Neo4j namespace")


class RetrieveOutput(BaseModel):
    """Output schema for retrieve_from_database tool."""
    chunks: List[Dict[str, Any]]
    source_ids: List[str]
    scores: List[float]


class RerankInput(BaseModel):
    """Input schema for rerank_results tool."""
    query: str
    chunks: List[Dict[str, Any]]
    top_n: int = Field(5, description="Top results after reranking")


class RerankOutput(BaseModel):
    """Output schema for rerank_results tool."""
    reranked_chunks: List[Dict[str, Any]]
    rerank_scores: List[float]


class GenerateInput(BaseModel):
    """Input schema for generate_answer tool."""
    query: str
    context_chunks: List[Dict[str, Any]]


class GenerateOutput(BaseModel):
    """Output schema for generate_answer tool."""
    answer: str
    citations: List[str]


# Tool Registry
TOOLS = [
    {
        "name": ToolName.RETRIEVE,
        "description": "Retrieve relevant chunks from Neo4j Test_rel_2 namespace using text matching",
        "input_schema": RetrieveInput,
        "output_schema": RetrieveOutput
    },
    {
        "name": ToolName.RERANK,
        "description": "Rerank retrieved chunks using BGE cross-encoder for better relevance",
        "input_schema": RerankInput,
        "output_schema": RerankOutput
    },
    {
        "name": ToolName.GENERATE,
        "description": "Generate answer from context using LLM synthesis",
        "input_schema": GenerateInput,
        "output_schema": GenerateOutput
    }
]


def retrieve_from_database(
    prompt: str,
    top_k: int = 10,
    namespace: str = "Test_rel_2"
) -> RetrieveOutput:
    """
    Retrieve relevant chunks from Neo4j.

    This implements exact word matching retrieval from the Neo4j database.
    For embedding-based retrieval, user should extend this with their embedding model.

    Retrieval Strategy Used: Exact match (mode 6 from batch_retrieve_neo4j.py)
    - Splits query into words
    - Matches nodes containing those words
    - Ranks by match count

    Reference: Document-Graph-Representation/shared_functions/batch_retrieve_neo4j.py

    TODO for user: To use embedding-based retrieval:
    1. Generate embedding for prompt using PhoBERT or similar
    2. Use gds.similarity.cosine() in Cypher query
    3. Integrate with existing batch_retrieve_neo4j.py patterns
    """
    client = get_neo4j_client()

    # Exact match retrieval (similar to mode 6 in batch_retrieve_neo4j.py)
    query = f"""
    WITH $query AS input
    WITH split(toLower(input), " ") AS words
    MATCH (n:{namespace})
    WHERE n.text IS NOT NULL

    // Count how many words from input appear in n.text
    WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count
    WHERE match_count > 0

    RETURN n.id AS id, n.text AS text, toFloat(match_count) AS score
    ORDER BY match_count DESC
    LIMIT $top_k
    """

    try:
        results = client.execute_query(query, {"query": prompt, "top_k": top_k})

        chunks = [{"id": r.get("id", ""), "text": r.get("text", "")} for r in results]
        scores = [r.get("score", 0.0) for r in results]
        source_ids = [r.get("id", "") for r in results]

        return RetrieveOutput(chunks=chunks, source_ids=source_ids, scores=scores)

    except Exception as e:
        # Return empty result on error
        return RetrieveOutput(chunks=[], source_ids=[], scores=[])


def get_tool_descriptions() -> List[Dict[str, str]]:
    """Get tool descriptions for LLM routing."""
    return [
        {"name": t["name"].value, "description": t["description"]}
        for t in TOOLS
    ]
