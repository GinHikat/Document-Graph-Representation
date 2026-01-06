"""Pydantic schemas for RAG tools."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class ToolName(str, Enum):
    """Available tool names."""
    RETRIEVE = "retrieve_from_database"
    RETRIEVE_GRAPH = "retrieve_with_graph_context"
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


class GraphRetrieveOutput(BaseModel):
    """Output schema for graph-enhanced retrieval."""
    chunks: List[Dict[str, Any]]
    source_ids: List[str]
    scores: List[float]
    graph_context: List[Dict[str, Any]]  # Related nodes via relationships
    cypher_query: str
    embedding_used: bool = True  # Whether embedding reranking was used
    warnings: List[str] = []  # Any degradation warnings


# Tool Registry
TOOLS = [
    {
        "name": ToolName.RETRIEVE,
        "description": "Retrieve relevant chunks using word-match (Vector baseline)",
        "input_schema": RetrieveInput,
        "output_schema": RetrieveOutput
    },
    {
        "name": ToolName.RETRIEVE_GRAPH,
        "description": "Retrieve with graph context: word-match + embedding rerank + graph traversal",
        "input_schema": RetrieveInput,
        "output_schema": GraphRetrieveOutput
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


def get_tool_descriptions() -> List[Dict[str, str]]:
    """Get tool descriptions for LLM routing."""
    return [
        {"name": t["name"].value, "description": t["description"]}
        for t in TOOLS
    ]
