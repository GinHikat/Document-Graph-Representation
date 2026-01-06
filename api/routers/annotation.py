"""Annotation router - QA annotation endpoints."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import List

from api.schemas import (
    AnnotationSubmitRequest,
    AnnotationResponse,
    AnnotationTask,
    AnnotatorStats,
    SimpleAnnotationRequest
)
from api.services.annotation import get_annotation_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.post("/submit", response_model=AnnotationResponse)
async def submit_annotation(request: AnnotationSubmitRequest):
    """Submit detailed annotation rating."""
    try:
        service = get_annotation_service()
        annotation_id = service.submit_annotation(
            question_id=request.questionId,
            user_id="anonymous",  # In production, get from auth
            overall_comparison=request.overallComparison,
            vector_correctness=request.vectorCorrectness,
            vector_completeness=request.vectorCompleteness,
            vector_relevance=request.vectorRelevance,
            graph_correctness=request.graphCorrectness,
            graph_completeness=request.graphCompleteness,
            graph_relevance=request.graphRelevance,
            comment=request.comment
        )
        return AnnotationResponse(
            id=annotation_id,
            message="Annotation submitted successfully"
        )
    except Exception as e:
        logger.error(f"Failed to submit annotation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simple", response_model=AnnotationResponse)
async def submit_simple_annotation(request: SimpleAnnotationRequest):
    """Submit simple preference annotation (from QA page)."""
    try:
        service = get_annotation_service()
        annotation_id = service.submit_simple_annotation(
            question_id=request.questionId,
            user_id="anonymous",
            preference=request.preference,
            comment=request.comment
        )
        return AnnotationResponse(
            id=annotation_id,
            message="Annotation submitted successfully"
        )
    except Exception as e:
        logger.error(f"Failed to submit simple annotation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending", response_model=List[AnnotationTask])
async def get_pending_tasks():
    """Get pending annotation tasks."""
    try:
        service = get_annotation_service()
        tasks = service.get_pending_tasks(user_id="anonymous", limit=10)
        return tasks
    except Exception as e:
        logger.error(f"Failed to get pending tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=AnnotatorStats)
async def get_stats():
    """Get annotator statistics."""
    try:
        service = get_annotation_service()
        stats = service.get_stats(user_id="anonymous")
        return stats
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
