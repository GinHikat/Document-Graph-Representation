"""Annotation service - manages annotation persistence in Neo4j."""
import uuid
from datetime import datetime, date
from typing import List, Optional
from api.db.neo4j import get_neo4j_client


class AnnotationService:
    """Service for managing QA annotations."""

    def submit_annotation(
        self,
        question_id: str,
        user_id: str,
        overall_comparison: str,
        vector_correctness: int = 0,
        vector_completeness: int = 0,
        vector_relevance: int = 0,
        graph_correctness: int = 0,
        graph_completeness: int = 0,
        graph_relevance: int = 0,
        comment: Optional[str] = None
    ) -> str:
        """Submit annotation rating to Neo4j."""
        client = get_neo4j_client()
        annotation_id = f"ann_{uuid.uuid4().hex[:8]}"

        query = """
        CREATE (a:Annotation {
            id: $id,
            questionId: $questionId,
            userId: $userId,
            vectorCorrectness: $vectorCorrectness,
            vectorCompleteness: $vectorCompleteness,
            vectorRelevance: $vectorRelevance,
            graphCorrectness: $graphCorrectness,
            graphCompleteness: $graphCompleteness,
            graphRelevance: $graphRelevance,
            overallComparison: $overallComparison,
            comment: $comment,
            createdAt: datetime()
        })
        RETURN a.id as id
        """

        result = client.execute_query(query, {
            "id": annotation_id,
            "questionId": question_id,
            "userId": user_id,
            "vectorCorrectness": vector_correctness,
            "vectorCompleteness": vector_completeness,
            "vectorRelevance": vector_relevance,
            "graphCorrectness": graph_correctness,
            "graphCompleteness": graph_completeness,
            "graphRelevance": graph_relevance,
            "overallComparison": overall_comparison,
            "comment": comment or ""
        })

        return result[0]["id"] if result else annotation_id

    def submit_simple_annotation(
        self,
        question_id: str,
        user_id: str,
        preference: str,
        comment: Optional[str] = None
    ) -> str:
        """Submit simple preference annotation."""
        return self.submit_annotation(
            question_id=question_id,
            user_id=user_id,
            overall_comparison=preference,
            comment=comment
        )

    def get_pending_tasks(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get pending annotation tasks for user.

        Returns sample tasks - in production would query actual questions
        that haven't been annotated by this user.
        """
        client = get_neo4j_client()

        # Get questions from Test_rel_2 nodes that haven't been annotated
        query = """
        MATCH (n:Test_rel_2)
        WHERE n.text IS NOT NULL AND n.text <> ''
        AND NOT EXISTS {
            MATCH (a:Annotation {questionId: n.id, userId: $userId})
        }
        RETURN n.id as id, n.text as text
        LIMIT $limit
        """

        results = client.execute_query(query, {"userId": user_id, "limit": limit})

        tasks = []
        for i, r in enumerate(results):
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            question_text = r.get("text", "")[:200] if r.get("text") else "Sample question"

            tasks.append({
                "id": task_id,
                "questionId": r.get("id", f"q_{i}"),
                "question": question_text,
                "vectorAnswer": {
                    "answer": "Vector-based answer would appear here.",
                    "sources": [],
                    "metrics": {"latencyMs": 500, "chunksUsed": 5}
                },
                "graphAnswer": {
                    "answer": "Graph-enhanced answer would appear here.",
                    "sources": [],
                    "metrics": {"latencyMs": 800, "chunksUsed": 3, "graphNodesUsed": 10, "graphHops": 2},
                    "cypherQuery": None,
                    "graphContext": []
                },
                "status": "pending"
            })

        return tasks

    def get_stats(self, user_id: str) -> dict:
        """Get annotation statistics for user."""
        client = get_neo4j_client()

        # Total annotations by user
        total_query = """
        MATCH (a:Annotation {userId: $userId})
        RETURN count(a) as total
        """
        total_result = client.execute_query(total_query, {"userId": user_id})
        total = total_result[0]["total"] if total_result else 0

        # Today's annotations
        today_query = """
        MATCH (a:Annotation {userId: $userId})
        WHERE date(a.createdAt) = date()
        RETURN count(a) as today
        """
        try:
            today_result = client.execute_query(today_query, {"userId": user_id})
            today = today_result[0]["today"] if today_result else 0
        except Exception:
            # Fallback if date() function not supported or query fails
            today = 0

        # Pending count (total nodes - annotated)
        pending_query = """
        MATCH (n:Test_rel_2)
        WHERE n.text IS NOT NULL
        RETURN count(n) as total
        """
        pending_result = client.execute_query(pending_query, {})
        total_questions = pending_result[0]["total"] if pending_result else 0
        pending = max(0, total_questions - total)

        # Calculate agreement rate (simplified - actual would compare with other annotators)
        agreement_rate = 0.85 if total > 0 else 0.0

        return {
            "totalAssigned": total_questions,
            "completedToday": today,
            "pendingReview": pending,
            "agreementRate": agreement_rate
        }


# Singleton instance
_annotation_service = None


def get_annotation_service() -> AnnotationService:
    """Get annotation service singleton."""
    global _annotation_service
    if _annotation_service is None:
        _annotation_service = AnnotationService()
    return _annotation_service
