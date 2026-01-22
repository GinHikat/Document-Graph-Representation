"""Document processing service for extracting text, chunking, and preparing for Neo4j indexing.

Ports logic from rag_model/model/Final_pipeline/final_doc_processor.py
to work as an API service with singleton pattern for heavy model loading.
"""
import os
import re
import logging
import unicodedata
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from pathlib import Path

import pdfplumber
import PyPDF2

logger = logging.getLogger(__name__)

# Lazy-loaded singletons
_processor_instance = None


class DocumentProcessor:
    """Process legal documents: extract text, parse structure, prepare chunks."""

    # Document type validation
    VALID_DOC_TYPES = ['Luật', 'Nghị Định', 'Nghị Quyết', 'Quyết Định', 'Thông Tư']

    def __init__(self):
        """Initialize without loading heavy models yet."""
        self._ner = None
        self._re_model = None

    def _get_ner(self):
        """Lazy load NER model."""
        if self._ner is None:
            try:
                from rag_model.model.NER.final_ner import NER
                self._ner = NER()
                logger.info("NER model loaded")
            except ImportError as e:
                logger.warning(f"NER model not available: {e}")
                self._ner = None
        return self._ner

    def _get_re_model(self):
        """Lazy load RE model."""
        if self._re_model is None:
            try:
                from rag_model.model.RE.final_re import RE
                self._re_model = RE()
                logger.info("RE model loaded")
            except ImportError as e:
                logger.warning(f"RE model not available: {e}")
                self._re_model = None
        return self._re_model

    def extract_text(self, filepath: str) -> str:
        """Extract text from PDF, DOCX, or TXT file.

        Args:
            filepath: Path to the document file

        Returns:
            Extracted text content
        """
        ext = Path(filepath).suffix.lower()

        if ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()

        if ext in ['.doc', '.docx']:
            # Convert to PDF first if needed
            try:
                import docx
                doc = docx.Document(filepath)
                return '\n'.join([p.text for p in doc.paragraphs])
            except Exception as e:
                logger.error(f"Failed to read DOCX: {e}")
                raise

        if ext == '.pdf':
            return self._extract_pdf_text(filepath)

        raise ValueError(f"Unsupported file type: {ext}")

    def _extract_pdf_text(self, filepath: str) -> str:
        """Extract text from PDF using pdfplumber with PyPDF2 fallback."""
        try:
            text = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            return text
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            try:
                reader = PyPDF2.PdfReader(filepath)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as e2:
                logger.error(f"Both PDF extractors failed: {e2}")
                raise

    def normalize_text(self, text: str) -> str:
        """Normalize unicode and clean text."""
        text = unicodedata.normalize("NFKC", text)
        text = text.replace("\u00A0", " ").replace("\u202F", " ").replace("\u200B", "")
        return text.strip()

    def parse_legal_text(self, text: str) -> Dict[str, Any]:
        """Parse legal document into hierarchical structure.

        Returns structure like:
        {
            "chapters": {
                "chapter I": {
                    "title": "...",
                    "text": "...",
                    "clauses": [{"clause": "1", "text": "...", "points": [...]}]
                }
            }
        }
        """
        clean_lines = [self.normalize_text(line) for line in text.splitlines()]
        clean_text = "\n".join(clean_lines)

        # Patterns for Vietnamese legal document structure
        chapter_pattern = r"(?i)^\s*chương\s+([IVXLCDM\d]+)\b"
        clause_pattern = r"^\s*Điều\s+(\d+)\b"
        point_pattern = r"^\s*(\d+)\."
        subpoint_pattern = r"^\s*([a-z])\)"

        has_chapter = any(re.match(chapter_pattern, line) for line in clean_lines)

        structure: Dict[str, Any] = OrderedDict()
        if has_chapter:
            structure["chapters"] = OrderedDict()
        else:
            structure["clauses"] = []

        current_chapter = None
        current_clause = None
        current_point = None
        current_subpoint = None

        for line in clean_lines:
            if not line:
                continue

            # Chapter
            mch = re.match(chapter_pattern, line)
            if mch and has_chapter:
                chap_key = f"chapter_{mch.group(1)}"
                structure["chapters"][chap_key] = {
                    "title": line,
                    "text": "",
                    "clauses": []
                }
                current_chapter = chap_key
                current_clause = current_point = current_subpoint = None
                continue

            # Clause (Điều)
            mcl = re.match(clause_pattern, line)
            if mcl:
                clause_entry = {"clause": mcl.group(1), "text": line, "points": []}
                if has_chapter:
                    if current_chapter is None:
                        current_chapter = "no_chapter"
                        structure["chapters"].setdefault(current_chapter, {"title": "", "text": "", "clauses": []})
                    structure["chapters"][current_chapter]["clauses"].append(clause_entry)
                else:
                    structure["clauses"].append(clause_entry)
                current_clause = clause_entry
                current_point = current_subpoint = None
                continue

            # Point (1.)
            mp = re.match(point_pattern, line)
            if mp and current_clause is not None:
                current_point = {"point": mp.group(1), "text": line, "subpoints": []}
                current_clause["points"].append(current_point)
                current_subpoint = None
                continue

            # Subpoint (a))
            ms = re.match(subpoint_pattern, line)
            if ms and current_point is not None:
                current_subpoint = {"subpoint": ms.group(1), "text": line}
                current_point["subpoints"].append(current_subpoint)
                continue

            # Continuation of content
            if current_subpoint is not None:
                current_subpoint["text"] += "\n" + line
            elif current_point is not None:
                current_point["text"] += "\n" + line
            elif current_clause is not None:
                current_clause["text"] += "\n" + line
            elif has_chapter and current_chapter is not None:
                prev = structure["chapters"][current_chapter]["text"]
                structure["chapters"][current_chapter]["text"] = (prev + "\n" + line) if prev else line

        return structure

    def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract document metadata using NER if available."""
        ner = self._get_ner()
        if ner is None:
            return self._extract_metadata_regex(text)

        try:
            df = ner.extract_document_metadata(text)
            return {
                "document_id": df['document_id'].iloc[0] if not df.empty else "",
                "document_type": df['document_type'].iloc[0] if not df.empty else "",
                "title": df['title'].iloc[0] if not df.empty else "",
                "issue_date": df['issue_date'].iloc[0] if not df.empty else ""
            }
        except Exception as e:
            logger.warning(f"NER extraction failed, using regex: {e}")
            return self._extract_metadata_regex(text)

    def _extract_metadata_regex(self, text: str) -> Dict[str, Any]:
        """Fallback metadata extraction using regex."""
        # Try to extract document ID (e.g., 16/2023/QH15)
        doc_id_match = re.search(r'(\d+/\d{4}/[A-Z\d-]+)', text[:2000])

        # Try to extract document type
        doc_type = ""
        for t in self.VALID_DOC_TYPES:
            if t.lower() in text[:1000].lower():
                doc_type = t
                break

        return {
            "document_id": doc_id_match.group(1) if doc_id_match else "",
            "document_type": doc_type,
            "title": "",
            "issue_date": ""
        }

    def structure_to_chunks(self, structure: Dict, doc_id: str) -> List[Dict]:
        """Convert parsed structure to flat list of chunks for indexing.

        Each chunk has:
        - id: Unique identifier (e.g., "16/2023/QH15_C_1_P_2")
        - text: Content text
        - type: chapter, clause, point, subpoint
        - parent_id: Reference to parent chunk
        """
        chunks = []

        if "chapters" in structure:
            for chap_key, chap in structure["chapters"].items():
                chap_id = f"{doc_id}_{chap_key}"
                chunks.append({
                    "id": chap_id,
                    "text": chap.get("text", ""),
                    "title": chap.get("title", ""),
                    "type": "chapter",
                    "parent_id": doc_id
                })

                for clause in chap.get("clauses", []):
                    clause_id = f"{chap_id}_C_{clause['clause']}"
                    chunks.append({
                        "id": clause_id,
                        "text": clause["text"],
                        "type": "clause",
                        "parent_id": chap_id
                    })

                    for point in clause.get("points", []):
                        point_id = f"{clause_id}_P_{point['point']}"
                        chunks.append({
                            "id": point_id,
                            "text": point["text"],
                            "type": "point",
                            "parent_id": clause_id
                        })

                        for subpoint in point.get("subpoints", []):
                            subpoint_id = f"{point_id}_SP_{subpoint['subpoint']}"
                            chunks.append({
                                "id": subpoint_id,
                                "text": subpoint["text"],
                                "type": "subpoint",
                                "parent_id": point_id
                            })
        else:
            # No chapters - flat clauses
            for clause in structure.get("clauses", []):
                clause_id = f"{doc_id}_C_{clause['clause']}"
                chunks.append({
                    "id": clause_id,
                    "text": clause["text"],
                    "type": "clause",
                    "parent_id": doc_id
                })

                for point in clause.get("points", []):
                    point_id = f"{clause_id}_P_{point['point']}"
                    chunks.append({
                        "id": point_id,
                        "text": point["text"],
                        "type": "point",
                        "parent_id": clause_id
                    })

                    for subpoint in point.get("subpoints", []):
                        subpoint_id = f"{point_id}_SP_{subpoint['subpoint']}"
                        chunks.append({
                            "id": subpoint_id,
                            "text": subpoint["text"],
                            "type": "subpoint",
                            "parent_id": point_id
                        })

        return chunks

    def process_document(self, filepath: str) -> Dict[str, Any]:
        """Full document processing pipeline.

        Args:
            filepath: Path to document file

        Returns:
            {
                "metadata": {...},
                "structure": {...},
                "chunks": [...]
            }
        """
        logger.info(f"Processing document: {filepath}")

        # Extract text
        text = self.extract_text(filepath)

        # Extract metadata
        metadata = self.extract_metadata(text)
        doc_id = metadata.get("document_id") or Path(filepath).stem

        # Parse structure
        structure = self.parse_legal_text(text)

        # Convert to chunks
        chunks = self.structure_to_chunks(structure, doc_id)

        logger.info(f"Processed {filepath}: {len(chunks)} chunks extracted")

        return {
            "metadata": metadata,
            "structure": structure,
            "chunks": chunks,
            "raw_text": text
        }


def get_document_processor() -> DocumentProcessor:
    """Get or create DocumentProcessor singleton."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = DocumentProcessor()
    return _processor_instance
