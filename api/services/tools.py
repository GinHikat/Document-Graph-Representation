"""Retrieval tools for RAG - Vector and Graph-enhanced retrieval.

Provides two retrieval modes:
1. Vector-only: Word-match baseline (simple keyword matching)
2. Graph-enhanced: Word-match + embedding rerank + graph traversal
"""
import logging
from typing import List, Dict, Any

from api.db.neo4j import get_neo4j_client
from api.services.embedding import embed_query
from api.services.rag_schemas import (
    RetrieveOutput,
    GraphRetrieveOutput,
    TOOLS,
    get_tool_descriptions,
)

logger = logging.getLogger(__name__)

# Retrieval configuration constants
WORD_MATCH_CANDIDATES = 20  # Initial candidates from word-match
EMBEDDING_RERANK_TOP_K = 5  # Top results after embedding rerank
GRAPH_RELATED_NODE_SCORE = 0.8  # Score multiplier for graph-expanded nodes
GRAPH_RELATED_LIMIT = 10  # Max related nodes per seed

# Re-export for backwards compatibility
__all__ = [
    "retrieve_from_database",
    "retrieve_with_graph_context",
    "get_tool_descriptions",
    "TOOLS",
    "RetrieveOutput",
    "GraphRetrieveOutput",
]


def retrieve_from_database(
    prompt: str,
    top_k: int = 10,
    namespace: str = "Test_rel_2"
) -> RetrieveOutput:
    """
    Retrieve relevant chunks using word-match (Vector baseline).

    This is the baseline retrieval - simple keyword matching without
    graph context. Used for comparison against graph-enhanced retrieval.
    """
    return _retrieve_word_match(prompt, top_k, namespace)


def _retrieve_word_match(
    prompt: str,
    top_k: int = 10,
    namespace: str = "Test_rel_2"
) -> RetrieveOutput:
    """Word-match retrieval using Neo4j text matching."""
    client = get_neo4j_client()

    query = f"""
    WITH $query AS input
    WITH split(toLower(input), " ") AS words
    MATCH (n:{namespace})
    WHERE n.text IS NOT NULL

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
        logger.debug(f"Word-match found {len(chunks)} results for: {prompt[:50]}...")
        return RetrieveOutput(chunks=chunks, source_ids=source_ids, scores=scores)
    except Exception as e:
        logger.error(f"Word-match retrieval failed for '{prompt[:50]}...': {e}")
        return RetrieveOutput(chunks=[], source_ids=[], scores=[])


def retrieve_with_graph_context(
    prompt: str,
    top_k: int = 10,
    namespace: str = "Test_rel_2",
    hop_depth: int = 1
) -> GraphRetrieveOutput:
    """
    Retrieve with graph context (hybrid: word-match + embedding rerank + graph expansion).

    This combines:
    1. Word-match to find seed nodes (top WORD_MATCH_CANDIDATES)
    2. Embedding-based reranking of seeds
    3. Graph traversal to get related nodes via relationships

    Provides richer context than word-only retrieval by leveraging
    the knowledge graph structure.
    """
    client = get_neo4j_client()
    embedding_used = True
    warnings = []

    # Get query embedding for reranking
    try:
        query_embedding = embed_query(prompt)
    except Exception as e:
        logger.warning(f"Embedding failed, using word-match only: {e}")
        query_embedding = None
        embedding_used = False
        warnings.append(f"Embedding unavailable: {str(e)[:50]}")

    # Build the graph query based on whether we have embeddings
    if query_embedding:
        graph_query = _build_graph_query_with_embedding(namespace)
        params = {"query": prompt, "emb": query_embedding, "top_k": top_k}
    else:
        graph_query = _build_graph_query_word_only(namespace)
        params = {"query": prompt, "top_k": top_k}

    try:
        results = client.execute_query(graph_query, params)
        return _process_graph_results(results, embedding_used, warnings)
    except Exception as e:
        logger.error(f"Graph retrieval failed for '{prompt[:50]}...': {e}")
        return GraphRetrieveOutput(
            chunks=[],
            source_ids=[],
            scores=[],
            graph_context=[],
            cypher_query=f"Error: {str(e)}",
            embedding_used=False,
            warnings=[str(e)]
        )


def _build_graph_query_with_embedding(namespace: str) -> str:
    """Build Cypher query with embedding-based reranking."""
    return f"""
    WITH $query AS input, $emb AS queryEmbedding
    WITH split(toLower(input), " ") AS words, queryEmbedding

    // Step 1: Find seed nodes via word-match
    MATCH (n:{namespace})
    WHERE n.text IS NOT NULL AND n.original_embedding IS NOT NULL

    WITH n, size([word IN words WHERE toLower(n.text) CONTAINS word]) AS match_count, queryEmbedding
    WHERE match_count > 0

    // Keep top candidates by word match
    ORDER BY match_count DESC
    LIMIT {WORD_MATCH_CANDIDATES}

    // Step 2: Rerank by embedding similarity
    WITH n, match_count, gds.similarity.cosine(n.original_embedding, queryEmbedding) AS sim_score
    ORDER BY sim_score DESC
    LIMIT {EMBEDDING_RERANK_TOP_K}

    // Step 3: Expand to related nodes via graph relationships
    WITH collect(n) AS seeds

    UNWIND seeds AS seed
    OPTIONAL MATCH (seed)-[r]-(related:{namespace})
    WHERE related.text IS NOT NULL

    WITH seed, related, r
    LIMIT {GRAPH_RELATED_LIMIT}

    // Combine seeds and related nodes
    WITH collect(DISTINCT {{
        id: seed.id,
        text: seed.text,
        score: 1.0,
        is_seed: true,
        relationship: null
    }}) AS seed_nodes,
    collect(DISTINCT CASE WHEN related IS NOT NULL THEN {{
        id: related.id,
        text: related.text,
        score: {GRAPH_RELATED_NODE_SCORE},
        is_seed: false,
        relationship: type(r)
    }} END) AS related_nodes

    // Flatten results
    UNWIND (seed_nodes + [x IN related_nodes WHERE x IS NOT NULL]) AS node
    WITH DISTINCT node.id AS id, node.text AS text, node.score AS score,
         node.is_seed AS is_seed, node.relationship AS relationship
    WHERE id IS NOT NULL

    RETURN id, text, score, is_seed, relationship
    ORDER BY score DESC, is_seed DESC
    LIMIT $top_k
    """


def _build_graph_query_word_only(namespace: str) -> str:
    """Build Cypher query with word-match only (fallback)."""
    return f"""
    WITH $query AS input
    WITH split(toLower(input), " ") AS words

    MATCH (seed:{namespace})
    WHERE seed.text IS NOT NULL
    WITH seed, size([word IN words WHERE toLower(seed.text) CONTAINS word]) AS match_count, words
    WHERE match_count > 0
    ORDER BY match_count DESC
    LIMIT {EMBEDDING_RERANK_TOP_K}

    WITH collect(seed) AS seeds

    UNWIND seeds AS seed
    OPTIONAL MATCH (seed)-[r]-(related:{namespace})
    WHERE related.text IS NOT NULL

    WITH seed, related, r
    LIMIT {GRAPH_RELATED_LIMIT}

    WITH collect(DISTINCT {{
        id: seed.id,
        text: seed.text,
        score: 1.0,
        is_seed: true,
        relationship: null
    }}) AS seed_nodes,
    collect(DISTINCT CASE WHEN related IS NOT NULL THEN {{
        id: related.id,
        text: related.text,
        score: {GRAPH_RELATED_NODE_SCORE},
        is_seed: false,
        relationship: type(r)
    }} END) AS related_nodes

    UNWIND (seed_nodes + [x IN related_nodes WHERE x IS NOT NULL]) AS node
    WITH DISTINCT node.id AS id, node.text AS text, node.score AS score,
         node.is_seed AS is_seed, node.relationship AS relationship
    WHERE id IS NOT NULL

    RETURN id, text, score, is_seed, relationship
    ORDER BY score DESC, is_seed DESC
    LIMIT $top_k
    """


def _process_graph_results(
    results: list,
    embedding_used: bool,
    warnings: list
) -> GraphRetrieveOutput:
    """Process graph query results into GraphRetrieveOutput."""
    chunks = []
    graph_context = []
    scores = []
    source_ids = []

    for r in results:
        node_data = {
            "id": r.get("id", ""),
            "text": r.get("text", ""),
            "is_seed": r.get("is_seed", True),
            "relationship": r.get("relationship")
        }

        chunks.append({"id": node_data["id"], "text": node_data["text"]})
        scores.append(r.get("score", 0.0))
        source_ids.append(node_data["id"])

        # Track graph context (related nodes via relationships)
        if not r.get("is_seed", True) and r.get("relationship"):
            graph_context.append({
                "node_id": node_data["id"],
                "relationship": r.get("relationship"),
                "text_preview": node_data["text"][:100] if node_data["text"] else ""
            })

    logger.debug(f"Graph search: {len(chunks)} results, {len(graph_context)} via graph")
    return GraphRetrieveOutput(
        chunks=chunks,
        source_ids=source_ids,
        scores=scores,
        graph_context=graph_context,
        cypher_query="hybrid_word_match_embedding_graph" if embedding_used else "word_match_graph",
        embedding_used=embedding_used,
        warnings=warnings
    )
