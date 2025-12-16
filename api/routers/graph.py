"""Graph API router for Neo4j operations."""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict

from api.schemas import (
    GraphData,
    CypherRequest,
    CypherResponse,
    GraphSchemaResponse
)
from api.db.neo4j import get_neo4j_client

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/nodes", response_model=GraphData)
async def get_graph_nodes(
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return")
):
    """
    Get Test_rel_2 graph nodes and relationships.
    Returns data in react-force-graph compatible format.
    """
    try:
        client = get_neo4j_client()
        data = client.get_test_rel_2_graph(limit=limit)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Neo4j query failed: {str(e)}"
        )


@router.post("/execute", response_model=CypherResponse)
async def execute_cypher(request: CypherRequest):
    """
    Execute arbitrary Cypher query.
    Security: Only MATCH queries are allowed (read-only).
    """
    try:
        # Security: Restrict to READ-ONLY queries
        query_upper = request.query.strip().upper()
        if not (query_upper.startswith("MATCH") or query_upper.startswith("WITH")):
            raise HTTPException(
                status_code=400,
                detail="Only MATCH or WITH queries allowed for security"
            )

        # Block write operations
        forbidden = ["CREATE", "DELETE", "MERGE", "SET", "REMOVE", "DROP"]
        for word in forbidden:
            if word in query_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Write operation '{word}' not allowed"
                )

        client = get_neo4j_client()
        results = client.execute_query(request.query, request.parameters)
        return CypherResponse(results=results, count=len(results))

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema", response_model=GraphSchemaResponse)
async def get_graph_schema():
    """Get Test_rel_2 namespace schema - labels, relationships, properties."""
    try:
        client = get_neo4j_client()
        schema = client.get_graph_schema()
        return GraphSchemaResponse(**schema)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats():
    """Get basic graph statistics."""
    try:
        client = get_neo4j_client()

        # Get counts
        node_count = client.get_node_count("Test_rel_2")

        # Get relationship count
        rel_query = """
        MATCH (:Test_rel_2)-[r]-(:Test_rel_2)
        RETURN count(r) as count
        """
        rel_result = client.execute_query(rel_query)
        rel_count = rel_result[0]['count'] if rel_result else 0

        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "avg_connections": rel_count / node_count if node_count > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
