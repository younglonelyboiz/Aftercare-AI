"""
PDF to Markdown converter module.
Trích xuất tài liệu PDF phác đồ y khoa sang Markdown đã làm sạch.
"""

from pathlib import Path
from typing import Union
from .cleaner import clean_rag_markdown

def extract_and_clean_pdf(pdf_path: Union[str, Path], output_md_path: Union[str, Path]) -> str:
    """
    Trích xuất nội dung từ PDF sang Markdown, làm sạch và lưu file UTF-8.
    """
    import pymupdf4llm

    pdf_file = Path(pdf_path)
    output_file = Path(output_md_path)

    if not pdf_file.exists():
        raise FileNotFoundError(f"Không tìm thấy file PDF tại: {pdf_file}")

    print(f"[Step 1] Đang trích xuất Markdown từ PDF: {pdf_file.name}...")
    raw_markdown = pymupdf4llm.to_markdown(str(pdf_file))

    print("[Step 1] Đang dọn dẹp và chuẩn hóa văn bản...")
    clean_markdown = clean_rag_markdown(raw_markdown)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(clean_markdown.encode("utf-8"))
    print(f"[Step 1] Thành công! Đã lưu file Markdown sạch tại: {output_file}")

    return clean_markdown

