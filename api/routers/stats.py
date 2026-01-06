"""Stats router for system metrics and dashboard data."""
import logging
import time
from typing import Optional
from collections import deque
import threading

from fastapi import APIRouter
from pydantic import BaseModel

from api.db.neo4j import get_neo4j_client
from api.services.qa_questions import get_sample_questions
from api.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stats", tags=["stats"])


class SystemStats(BaseModel):
    """System statistics for dashboard display."""
    document_count: int
    question_count: int
    relationship_count: int
    avg_connections: float
    accuracy_rate: Optional[float] = None
    avg_response_time: Optional[float] = None


# Thread-safe response time storage using deque with fixed size
_response_times: deque = deque(maxlen=100)
_response_times_lock = threading.Lock()


def record_response_time(duration_seconds: float):
    """Record a RAG query response time for averaging."""
    if duration_seconds > 0 and duration_seconds < 300:  # Reasonable range
        with _response_times_lock:
            _response_times.append(duration_seconds)


def get_avg_response_time() -> Optional[float]:
    """Get average response time from recorded queries."""
    with _response_times_lock:
        if not _response_times:
            return None
        return sum(_response_times) / len(_response_times)


@router.get("", response_model=SystemStats)
async def get_system_stats():
    """
    Get system statistics for dashboard.

    Returns:
    - document_count: Number of nodes in Neo4j graph
    - question_count: Number of QA pairs available
    - relationship_count: Number of edges in graph
    - avg_connections: Average connections per node
    - accuracy_rate: Evaluation accuracy (if available)
    - avg_response_time: Average RAG query time (if available)
    """
    try:
        neo4j = get_neo4j_client()

        # Get graph stats using configured namespace
        namespace = config.DEFAULT_NAMESPACE
        stats_query = f"""
        MATCH (n:{namespace})
        WITH count(n) as nodeCount
        OPTIONAL MATCH (:{namespace})-[r]->(:{namespace})
        WITH nodeCount, count(r) as relCount
        RETURN nodeCount, relCount,
               CASE WHEN nodeCount > 0 THEN toFloat(relCount) / nodeCount ELSE 0 END as avgConn
        """

        result = neo4j.execute_query(stats_query)

        if result:
            node_count = result[0].get('nodeCount', 0)
            rel_count = result[0].get('relCount', 0)
            avg_conn = result[0].get('avgConn', 0)
        else:
            node_count = neo4j.get_node_count(config.DEFAULT_NAMESPACE)
            rel_count = 0
            avg_conn = 0

        # Get question count from QA service
        questions = get_sample_questions(count=1000, shuffle=False)
        question_count = len(questions)

        # Get average response time if available
        avg_time = get_avg_response_time()

        logger.info(f"Stats: {node_count} nodes, {question_count} questions, {rel_count} relationships")

        return SystemStats(
            document_count=node_count,
            question_count=question_count,
            relationship_count=rel_count,
            avg_connections=round(avg_conn, 2),
            accuracy_rate=None,  # No real evaluation data yet
            avg_response_time=round(avg_time, 2) if avg_time else None
        )

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return SystemStats(
            document_count=0,
            question_count=0,
            relationship_count=0,
            avg_connections=0,
            accuracy_rate=None,
            avg_response_time=None
        )
