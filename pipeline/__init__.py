"""
RAG Sub-package for Aftercare-AI.
Cung cấp các công cụ trích xuất, phân đoạn, nhúng vector và chuẩn hóa tri thức y khoa.
"""

from .cleaner import clean_rag_markdown
from .converter import extract_and_clean_pdf
from .chunker import split_markdown_by_headers, chunk_page_indexed_records
from .embedder import GeminiRAGService, LLMExtractedMetadata
from .embedder_bge_m3 import BGEM3Embedder
from .ingest_to_pgvector import ingest_chunks_to_pgvector
from .formatter import compact_vector_in_existing_json, compact_vector_json_string
from .pipeline import RAGPipeline

__all__ = [
    "clean_rag_markdown",
    "extract_and_clean_pdf",
    "split_markdown_by_headers",
    "chunk_page_indexed_records",
    "GeminiRAGService",
    "LLMExtractedMetadata",
    "BGEM3Embedder",
    "ingest_chunks_to_pgvector",
    "compact_vector_in_existing_json",
    "compact_vector_json_string",
    "RAGPipeline",
]