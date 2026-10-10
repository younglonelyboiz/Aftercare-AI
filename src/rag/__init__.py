"""
RAG Sub-package for Aftercare-AI.
Cung cấp các công cụ trích xuất, phân đoạn, nhúng vector và chuẩn hóa tri thức y khoa.
"""

from .cleaner import clean_rag_markdown
from .converter import extract_and_clean_pdf
from .chunker import split_markdown_by_headers
from .embedder import GeminiRAGService, LLMExtractedMetadata
from .formatter import compact_vector_in_existing_json, compact_vector_json_string
from .pipeline import RAGPipeline

__all__ = [
    "clean_rag_markdown",
    "extract_and_clean_pdf",
    "split_markdown_by_headers",
    "GeminiRAGService",
    "LLMExtractedMetadata",
    "compact_vector_in_existing_json",
    "compact_vector_json_string",
    "RAGPipeline",
]

