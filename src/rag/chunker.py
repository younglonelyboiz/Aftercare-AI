"""
Markdown Semantic Chunker module.
Phân mảnh văn bản Markdown theo cấu trúc tiêu đề (Header 1, 2, 3) để bảo toàn ngữ cảnh y khoa.
"""

from typing import List, Dict, Any

DEFAULT_HEADERS_TO_SPLIT_ON = [
    ("#", "Header_1"),
    ("##", "Header_2"),
    ("###", "Header_3"),
]

def split_markdown_by_headers(
    text: str,
    headers_to_split_on: List[tuple] = None,
    min_chunk_length: int = 20
) -> List[Dict[str, Any]]:
    """
    Tách tài liệu Markdown thành danh sách các đoạn (chunks) theo tiêu đề ngữ nghĩa.
    Trả về danh sách dict gồm 'content', 'metadata', và 'citation_title'.
    """
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter
    except ImportError:
        raise ImportError(
            "Chưa cài đặt thư viện 'langchain-text-splitters'. "
            "Vui lòng cài đặt bằng: pip install langchain-text-splitters"
        )

    if headers_to_split_on is None:
        headers_to_split_on = DEFAULT_HEADERS_TO_SPLIT_ON

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    doc_chunks = markdown_splitter.split_text(text)
    processed_chunks: List[Dict[str, Any]] = []

    for chunk in doc_chunks:
        content = chunk.page_content.strip()
        if not content or len(content) < min_chunk_length:
            continue

        header_meta = chunk.metadata
        section_title = (
            header_meta.get("Header_3")
            or header_meta.get("Header_2")
            or header_meta.get("Header_1")
            or "Thông tin chung"
        )

        processed_chunks.append({
            "content": content,
            "header_metadata": header_meta,
            "section_title": section_title.strip()
        })

    return processed_chunks
