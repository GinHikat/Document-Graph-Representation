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


# ============ Annotation Schemas ============

class AnnotationSubmitRequest(BaseModel):
    """Request for submitting annotation rating."""
    questionId: str = Field(..., description="Question ID being annotated")
    vectorCorrectness: int = Field(default=0, ge=0, le=5)
    vectorCompleteness: int = Field(default=0, ge=0, le=5)
    vectorRelevance: int = Field(default=0, ge=0, le=5)
    graphCorrectness: int = Field(default=0, ge=0, le=5)
    graphCompleteness: int = Field(default=0, ge=0, le=5)
    graphRelevance: int = Field(default=0, ge=0, le=5)
    overallComparison: str = Field(..., description="vector_much_better|vector_better|equivalent|graph_better|graph_much_better")
    comment: Optional[str] = None


class AnnotationResponse(BaseModel):
    """Response after submitting annotation."""
    id: str
    message: str


class QAMetrics(BaseModel):
    """QA result metrics."""
    latencyMs: int = 0
    chunksUsed: int = 0
    confidenceScore: Optional[float] = None
    graphNodesUsed: Optional[int] = None
    graphHops: Optional[int] = None


class QAAnswer(BaseModel):
    """QA answer with sources and metrics."""
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: QAMetrics
    cypherQuery: Optional[str] = None
    graphContext: List[Dict[str, Any]] = Field(default_factory=list)


class AnnotationTask(BaseModel):
    """Pending annotation task."""
    id: str
    questionId: str
    question: str
    vectorAnswer: QAAnswer
    graphAnswer: QAAnswer
    status: str = "pending"


class AnnotatorStats(BaseModel):
    """Annotator statistics."""
    totalAssigned: int
    completedToday: int
    pendingReview: int
    agreementRate: float


class SimpleAnnotationRequest(BaseModel):
    """Simple annotation with just preference."""
    questionId: str
    preference: str = Field(..., description="vector|equivalent|graph|both_wrong")
    comment: Optional[str] = None
