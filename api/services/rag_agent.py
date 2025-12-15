"""RAG Agent with tool-calling pattern and streaming support."""
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional

from api.services.tools import (
    retrieve_from_database,
    RetrieveOutput,
    ToolName,
    TOOLS
)
from api.services.reranker import rerank_chunks

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    RAG Agent using tool-calling pattern.

    Flow:
    1. receive query
    2. call retrieve_from_database(prompt)
    3. call rerank_results(query, chunks)
    4. call generate_answer(query, context)
    5. return answer with sources

    Supports streaming via SSE (Server-Sent Events).
    """

    def __init__(self, tools: List[Dict] = None):
        """Initialize RAG agent with tool registry."""
        self.tools = {t["name"]: t for t in (tools or TOOLS)}

    async def query(self, user_query: str) -> AsyncGenerator[str, None]:
        """
        Process query using tool-calling pattern with streaming.

        Yields SSE events:
        - {"type": "tool_start", "tool": "retrieve_from_database"}
        - {"type": "tool_end", "tool": "retrieve_from_database", "result": {...}}
        - {"type": "text", "delta": "The answer is..."}
        - {"type": "done"}

        Args:
            user_query: User's question

        Yields:
            SSE-formatted event strings
        """
        logger.info(f"Processing RAG query: {user_query[:50]}...")

        # Step 1: Retrieval
        yield self._sse_event({"type": "tool_start", "tool": "retrieve_from_database"})

        try:
            retrieve_result = retrieve_from_database(
                prompt=user_query,
                top_k=20,
                namespace="Test_rel_2"
            )
            chunks_found = len(retrieve_result.chunks)
            logger.info(f"Retrieved {chunks_found} chunks")

            yield self._sse_event({
                "type": "tool_end",
                "tool": "retrieve_from_database",
                "chunks": chunks_found,
                "source_ids": retrieve_result.source_ids[:5]  # First 5 for preview
            })

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            yield self._sse_event({
                "type": "error",
                "message": f"Retrieval failed: {str(e)}"
            })
            yield self._sse_event({"type": "done"})
            return

        # Step 2: Reranking
        yield self._sse_event({"type": "tool_start", "tool": "rerank_results"})

        try:
            reranked_chunks, rerank_scores = rerank_chunks(
                query=user_query,
                chunks=retrieve_result.chunks,
                top_n=5
            )
            logger.info(f"Reranked to {len(reranked_chunks)} chunks")

            yield self._sse_event({
                "type": "tool_end",
                "tool": "rerank_results",
                "top_chunks": len(reranked_chunks),
                "top_score": rerank_scores[0] if rerank_scores else 0
            })

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            # Fall back to original chunks
            reranked_chunks = retrieve_result.chunks[:5]
            rerank_scores = retrieve_result.scores[:5]
            yield self._sse_event({
                "type": "tool_end",
                "tool": "rerank_results",
                "top_chunks": len(reranked_chunks),
                "fallback": True
            })

        # Step 3: Answer Generation
        yield self._sse_event({"type": "tool_start", "tool": "generate_answer"})

        # Generate answer (stub - user can implement LLM call)
        answer = self._generate_answer_stub(user_query, reranked_chunks)

        # Stream answer token by token
        words = answer.split()
        for i, word in enumerate(words):
            yield self._sse_event({"type": "text", "delta": word + " "})

        # Send sources
        sources = [
            {
                "id": chunk.get("id", ""),
                "text": chunk.get("text", "")[:200],  # Truncate for response
                "score": score
            }
            for chunk, score in zip(reranked_chunks[:3], rerank_scores[:3])
        ]

        yield self._sse_event({
            "type": "sources",
            "sources": sources
        })

        yield self._sse_event({"type": "done"})

    async def query_non_streaming(self, user_query: str) -> Dict[str, Any]:
        """
        Non-streaming version of query.

        Returns complete response at once.
        """
        logger.info(f"Processing non-streaming RAG query: {user_query[:50]}...")

        # Retrieval
        retrieve_result = retrieve_from_database(
            prompt=user_query,
            top_k=20,
            namespace="Test_rel_2"
        )

        # Reranking
        reranked_chunks, rerank_scores = rerank_chunks(
            query=user_query,
            chunks=retrieve_result.chunks,
            top_n=5
        )

        # Generate answer
        answer = self._generate_answer_stub(user_query, reranked_chunks)

        # Format sources
        sources = [
            {
                "id": chunk.get("id", ""),
                "text": chunk.get("text", "")[:300],
                "score": score
            }
            for chunk, score in zip(reranked_chunks[:3], rerank_scores[:3])
        ]

        return {
            "answer": answer,
            "sources": sources,
            "metrics": {
                "chunks_retrieved": len(retrieve_result.chunks),
                "chunks_reranked": len(reranked_chunks),
                "top_score": rerank_scores[0] if rerank_scores else 0
            }
        }

    def _generate_answer_stub(self, query: str, context: List[Dict]) -> str:
        """
        Stub for answer generation.

        TODO: USER IMPLEMENTATION REQUIRED
        Replace this with actual LLM call:

        Example with OpenAI:
        ```python
        from openai import OpenAI
        client = OpenAI()

        context_text = "\\n\\n".join([c["text"] for c in context])
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a Vietnamese tax law expert. Answer based on the context provided."},
                {"role": "user", "content": f"Context:\\n{context_text}\\n\\nQuestion: {query}"}
            ]
        )
        return response.choices[0].message.content
        ```

        Example with Gemini:
        ```python
        import google.generativeai as genai
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(f"Context: {context_text}\\n\\nQuestion: {query}")
        return response.text
        ```
        """
        # Build context from chunks
        context_texts = []
        for i, chunk in enumerate(context[:3], 1):
            text = chunk.get("text", "")[:400]
            source_id = chunk.get("id", "unknown")
            context_texts.append(f"[{i}] {text} (Source: {source_id})")

        context_str = "\n\n".join(context_texts)

        # Stub response
        return f"""Dựa trên các tài liệu luật thuế liên quan, đây là thông tin tìm được về câu hỏi của bạn: "{query}"

{context_str}

---
[Lưu ý: Đây là phản hồi stub. Để có câu trả lời chính xác hơn, hãy tích hợp với LLM như OpenAI GPT-4, Google Gemini, hoặc Claude.]
"""

    def _sse_event(self, data: Dict) -> str:
        """Format data as SSE event."""
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# Singleton instance
_rag_agent = None


def get_rag_agent() -> RAGAgent:
    """Get or create RAG agent singleton."""
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent()
    return _rag_agent
