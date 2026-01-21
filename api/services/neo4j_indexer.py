"""Neo4j indexing service for document chunks with embeddings and relationships.

Creates nodes and relationships in Neo4j for RAG retrieval.
Uses Test_rel_2 namespace for consistency with existing data.
"""
import logging
from typing import List, Dict, Any, Optional

from api.db.neo4j import get_neo4j_client
from api.services.embedding import embed_texts, get_embedding_dimension

logger = logging.getLogger(__name__)

# Namespace for document nodes (consistent with existing data)
NAMESPACE = "Test_rel_2"


class Neo4jIndexer:
    """Index document chunks into Neo4j with embeddings and relationships."""

    def __init__(self):
        self.client = get_neo4j_client()
        self.namespace = NAMESPACE

    def create_document_node(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """Create or update document root node.

        Args:
            doc_id: Document identifier
            metadata: Document metadata (title, type, date, etc.)

        Returns:
            True if successful
        """
        query = f"""
        MERGE (d:{self.namespace}:Document {{id: $doc_id}})
        SET d.title = $title,
            d.document_type = $document_type,
            d.issue_date = $issue_date,
            d.indexed_at = datetime()
        RETURN d.id as id
        """
        try:
            result = self.client.execute_query(query, {
                "doc_id": doc_id,
                "title": metadata.get("title", ""),
                "document_type": metadata.get("document_type", ""),
                "issue_date": metadata.get("issue_date", "")
            })
            logger.info(f"Created document node: {doc_id}")
            return len(result) > 0
        except Exception as e:
            logger.error(f"Failed to create document node: {e}")
            return False

    def create_chunk_nodes(self, chunks: List[Dict], batch_size: int = 50) -> int:
        """Create chunk nodes with embeddings in batches.

        Args:
            chunks: List of chunk dicts with id, text, type, parent_id
            batch_size: Number of chunks to process at once

        Returns:
            Number of chunks indexed
        """
        total_indexed = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Filter out empty text chunks
            valid_chunks = [c for c in batch if c.get("text", "").strip()]
            if not valid_chunks:
                continue

            # Generate embeddings for batch
            texts = [c["text"] for c in valid_chunks]
            try:
                embeddings = embed_texts(texts)
            except Exception as e:
                logger.error(f"Embedding failed for batch {i}: {e}")
                continue

            # Create nodes with embeddings
            for chunk, embedding in zip(valid_chunks, embeddings):
                success = self._create_single_chunk(chunk, embedding)
                if success:
                    total_indexed += 1

        logger.info(f"Indexed {total_indexed}/{len(chunks)} chunks")
        return total_indexed

    def _create_single_chunk(self, chunk: Dict, embedding: List[float]) -> bool:
        """Create a single chunk node with embedding."""
        query = f"""
        MERGE (c:{self.namespace}:Chunk {{id: $id}})
        SET c.text = $text,
            c.type = $type,
            c.parent_id = $parent_id,
            c.original_embedding = $embedding,
            c.indexed_at = datetime()
        RETURN c.id as id
        """
        try:
            result = self.client.execute_query(query, {
                "id": chunk["id"],
                "text": chunk["text"][:10000],  # Limit text size
                "type": chunk.get("type", "chunk"),
                "parent_id": chunk.get("parent_id", ""),
                "embedding": embedding
            })
            return len(result) > 0
        except Exception as e:
            logger.error(f"Failed to create chunk {chunk['id']}: {e}")
            return False

    def create_hierarchy_relationships(self, chunks: List[Dict]) -> int:
        """Create CONTAINS relationships based on parent_id.

        Args:
            chunks: List of chunk dicts with id and parent_id

        Returns:
            Number of relationships created
        """
        created = 0
        for chunk in chunks:
            parent_id = chunk.get("parent_id")
            if not parent_id:
                continue

            query = f"""
            MATCH (parent:{self.namespace} {{id: $parent_id}})
            MATCH (child:{self.namespace} {{id: $child_id}})
            MERGE (parent)-[r:CONTAINS]->(child)
            RETURN type(r) as rel_type
            """
            try:
                result = self.client.execute_query(query, {
                    "parent_id": parent_id,
                    "child_id": chunk["id"]
                })
                if result:
                    created += 1
            except Exception as e:
                logger.warning(f"Failed to create relationship for {chunk['id']}: {e}")

        logger.info(f"Created {created} hierarchy relationships")
        return created

    def create_cross_references(self, doc_id: str, references: List[Dict]) -> int:
        """Create CITES/REFERENCES relationships between documents.

        Args:
            doc_id: Source document ID
            references: List of reference dicts with target_doc_id, target_clause

        Returns:
            Number of relationships created
        """
        created = 0
        for ref in references:
            target_id = ref.get("target_doc_id", "")
            if not target_id:
                continue

            query = f"""
            MATCH (source:{self.namespace} {{id: $source_id}})
            MATCH (target:{self.namespace})
            WHERE target.id STARTS WITH $target_doc_id
            MERGE (source)-[r:CITES]->(target)
            SET r.clause = $clause
            RETURN type(r) as rel_type
            """
            try:
                result = self.client.execute_query(query, {
                    "source_id": doc_id,
                    "target_doc_id": target_id,
                    "clause": ref.get("target_clause", "")
                })
                if result:
                    created += 1
            except Exception as e:
                logger.warning(f"Failed to create cross-reference: {e}")

        logger.info(f"Created {created} cross-reference relationships")
        return created

    def index_document(
        self,
        doc_id: str,
        metadata: Dict[str, Any],
        chunks: List[Dict],
        references: Optional[List[Dict]] = None
    ) -> Dict[str, int]:
        """Full document indexing pipeline.

        Args:
            doc_id: Document identifier
            metadata: Document metadata
            chunks: Parsed chunks with text
            references: Cross-document references

        Returns:
            Stats dict with counts
        """
        stats = {
            "document_created": 0,
            "chunks_indexed": 0,
            "relationships_created": 0,
            "references_created": 0
        }

        # 1. Create document node
        if self.create_document_node(doc_id, metadata):
            stats["document_created"] = 1

        # 2. Create chunk nodes with embeddings
        stats["chunks_indexed"] = self.create_chunk_nodes(chunks)

        # 3. Create hierarchy relationships
        stats["relationships_created"] = self.create_hierarchy_relationships(chunks)

        # 4. Create cross-references if provided
        if references:
            stats["references_created"] = self.create_cross_references(doc_id, references)

        logger.info(f"Document indexing complete: {stats}")
        return stats

    def delete_document(self, doc_id: str) -> int:
        """Delete document and all its chunks.

        Args:
            doc_id: Document ID to delete

        Returns:
            Number of nodes deleted
        """
        query = f"""
        MATCH (n:{self.namespace})
        WHERE n.id = $doc_id OR n.id STARTS WITH $doc_prefix
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        try:
            result = self.client.execute_query(query, {
                "doc_id": doc_id,
                "doc_prefix": f"{doc_id}_"
            })
            deleted = result[0]["deleted"] if result else 0
            logger.info(f"Deleted {deleted} nodes for document {doc_id}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return 0


# Singleton instance
_indexer_instance = None


def get_neo4j_indexer() -> Neo4jIndexer:
    """Get or create Neo4jIndexer singleton."""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = Neo4jIndexer()
    return _indexer_instance
