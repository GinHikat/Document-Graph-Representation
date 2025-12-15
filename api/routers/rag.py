"""RAG API router for query endpoints."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, List, Any
import logging

from api.schemas import (
    QueryRequest,
    RetrieveRequest,
    RetrieveResponse,
    RetrieveChunk,
    RerankRequest,
    RerankResponse
)
from api.services.rag_agent import get_rag_agent
from api.services.tools import retrieve_from_database
from api.services.reranker import rerank_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query")
async def query_rag_agent(request: QueryRequest):
    """
    Query RAG agent with streaming or non-streaming response.

    Streaming (default):
    - Returns SSE events in real-time
    - Events: tool_start, tool_end, text, sources, done

    Non-streaming:
    - Returns complete JSON response
    """
    agent = get_rag_agent()

    if request.stream:
        return StreamingResponse(
            agent.query(request.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    else:
        try:
            result = await agent.query_non_streaming(request.question)
            return result
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_chunks_endpoint(request: RetrieveRequest):
    """
    Direct access to retrieve_from_database tool.
    Useful for testing and debugging retrieval.
    """
    try:
        result = retrieve_from_database(
            prompt=request.prompt,
            top_k=request.top_k,
            namespace=request.namespace
        )

        # Convert to response format
        chunks = [
            RetrieveChunk(id=c.get("id", ""), text=c.get("text", ""), score=s)
            for c, s in zip(result.chunks, result.scores)
        ]

        return RetrieveResponse(
            chunks=chunks,
            source_ids=result.source_ids,
            scores=result.scores
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rerank", response_model=RerankResponse)
async def rerank_chunks_endpoint(request: RerankRequest):
    """
    Direct access to reranking tool.
    Useful for testing reranker quality.
    """
    try:
        reranked, scores = rerank_chunks(
            query=request.query,
            chunks=request.chunks,
            top_n=request.top_n
        )

        return RerankResponse(
            reranked_chunks=reranked,
            scores=scores
        )
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_tools():
    """List available RAG tools and their descriptions."""
    from api.services.tools import get_tool_descriptions
    return {"tools": get_tool_descriptions()}
