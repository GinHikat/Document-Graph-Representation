"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


# ============ Graph Schemas ============

class GraphNode(BaseModel):
    """Graph node representation matching frontend GraphNode type."""
    id: str
    label: str
    type: str = "document"
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphLink(BaseModel):
    """Graph link/relationship representation."""
    source: str
    target: str
    type: str
    properties: Optional[Dict[str, Any]] = None


class GraphData(BaseModel):
    """Graph data with nodes and links - compatible with react-force-graph."""
    nodes: List[GraphNode]
    links: List[GraphLink]


class CypherRequest(BaseModel):
    """Request for executing Cypher query."""
    query: str = Field(..., description="Cypher query to execute")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Query parameters")


class CypherResponse(BaseModel):
    """Response from Cypher query execution."""
    results: List[Dict[str, Any]]
    count: int


class GraphSchemaResponse(BaseModel):
    """Graph schema information."""
    labels: List[List[str]]
    relationships: List[str]
    properties: List[str]


# ============ Health Schemas ============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall status: healthy, degraded, or unhealthy")
    neo4j_connected: bool
    message: str
    node_count: Optional[int] = None


# ============ RAG Schemas ============

class RetrieveRequest(BaseModel):
    """Request for RAG retrieval."""
    prompt: str = Field(..., description="User query text")
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results to retrieve")
    namespace: str = Field(default="Test_rel_2", description="Neo4j namespace/label")


class RetrieveChunk(BaseModel):
    """Retrieved chunk from database."""
    id: str
    text: str
    score: float = 0.0


class RetrieveResponse(BaseModel):
    """Response from retrieval."""
    chunks: List[RetrieveChunk]
    source_ids: List[str]
    scores: List[float]


class RerankRequest(BaseModel):
    """Request for reranking chunks."""
    query: str
    chunks: List[Dict[str, Any]]
    top_n: int = Field(default=5, ge=1, le=20)


class RerankResponse(BaseModel):
    """Response from reranking."""
    reranked_chunks: List[Dict[str, Any]]
    scores: List[float]


class QueryRequest(BaseModel):
    """Request for RAG query."""
    question: str = Field(..., description="User question")
    stream: bool = Field(default=True, description="Whether to stream response")


class QueryResponse(BaseModel):
    """Non-streaming response from RAG query."""
    answer: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, Any]


# ============ SSE Event Types ============

class SSEEventType(str, Enum):
    """Server-Sent Event types."""
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TEXT = "text"
    DONE = "done"
    ERROR = "error"
