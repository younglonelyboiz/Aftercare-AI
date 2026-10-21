"""
Semantic Chunker module for Aftercare-AI.
Hỗ trợ cả phân mảnh Markdown Headers và Page-Aware Semantic Chunking (giữ nguyên Page Index, Tables và Safety Tiers).
"""

import re
from typing import List, Dict, Any

def split_markdown_by_headers(clean_text: str) -> list:
    """Tách markdown theo headers bằng pure Python regex."""
    lines = clean_text.split("\n")
    chunks = []
    current_title = "Thông tin chung"
    current_lines = []

    for line in lines:
        if line.startswith("#"):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if len(content) >= 20:
                    chunks.append({"content": content, "section_title": current_title})
                current_lines = []
            clean_h = re.sub(r'^#+\s*', '', line).strip()
            if clean_h:
                current_title = clean_h
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if len(content) >= 20:
            chunks.append({"content": content, "section_title": current_title})

    return chunks


def clean_text_in_chunk(text: str) -> str:
    """Làm sạch các lỗi chính tả OCR sót lại trong văn bản y khoa."""
    replacements = [
        (r'\bử trí\b', 'Xử trí'),
        (r'\bỬ trí\b', 'Xử trí'),
        (r'\bem xét\b', 'Xem xét'),
        (r'\bEm xét\b', 'Xem xét'),
        (r'\|\s*iều thấp\b', '| Liều thấp'),
        (r'\|\s*iều trung bình\b', '| Liều trung bình'),
        (r'\|\s*iều cao\b', '| Liều cao'),
        (r'\biều thấp\b', 'Liều thấp'),
        (r'\biều trung bình\b', 'Liều trung bình'),
        (r'\biều cao\b', 'Liều cao'),
        (r'\bIều thấp\b', 'Liều thấp'),
        (r'\bIều trung bình\b', 'Liều trung bình'),
        (r'\bIều cao\b', 'Liều cao'),
        (r'\bhenkhi\b', 'hen khi'),
        (r'\bkiểm soát henkhi\b', 'kiểm soát hen khi'),
        (r'\bđt kjch phát\b', 'đợt kịch phát'),
        (r'\bchôngviêm\b', 'chống viêm'),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text)
    return text


def split_text_into_semantic_blocks(content: str) -> List[str]:
    """
    Tách nội dung trang thành các khối ngữ nghĩa (semantic blocks):
    - Nhận diện cả \\n\\n (đoạn văn)
    - Nhận diện danh sách gạch đầu dòng (\\n- , \\n* , \\n• )
    - Nhận diện các đề mục số (ví dụ: \\n3.4.1. , \\n1. , \\n2. )
    """
    normalized = re.sub(r'([^\n])\n(- |\* |• |\d+\.\d+(\.\d+)?\s+)', r'\1\n\n\2', content)
    raw_blocks = [b.strip() for b in normalized.split("\n\n") if b.strip()]
    return raw_blocks


def chunk_page_indexed_records(
    page_records: List[Dict[str, Any]],
    max_chunk_chars: int = 1200,
    min_chunk_chars: int = 50,
    chunk_overlap: int = 100
) -> List[Dict[str, Any]]:
    """
    Phân mảnh dữ liệu y khoa theo từng trang đã được bóc tách và làm sạch.
    TỰ ĐỘNG ĐIỀN PAGE INDEX & METADATA VÀO TỪNG CHUNK CHO RAG:
    - page_index: Số trang (0-indexed) cho PDF viewer
    - pdf_page: Số trang trong file PDF gốc
    - printed_page: Số trang in của tài liệu
    - document_tag & document_name: Định danh tài liệu (BYT QĐ 1851 hoặc GINA 2023)
    - knowledge_store: Kho tri thức (Kho 1 Cấp cứu vs Kho 2 Chăm sóc tại nhà)
    - safety_tier: Mức độ an toàn y tế (CRITICAL_EMERGENCY, HIGH_RISK_WARNING, STANDARD_HOMECARE)
    - citation: Trích dẫn chuẩn để UI hiển thị trực tiếp cho người bệnh
    """
    chunks: List[Dict[str, Any]] = []

    for page in page_records:
        content = page.get("formatted_markdown", "").strip()
        if not content:
            continue

        content = clean_text_in_chunk(content)
        if len(content) < min_chunk_chars:
            continue

        doc_tag = page.get("document_tag", "unknown")
        doc_name = page.get("document", "Tài liệu Y khoa")
        pdf_page = page.get("pdf_page", 1)
        page_idx = page.get("page_index", pdf_page - 1)
        printed_page = page.get("printed_page")
        k_store = page.get("knowledge_store", "KHO_2_CHAM_SOC_HOI_PHUC_THEO_DOI")
        safety_tier = page.get("safety_tier", "STANDARD_HOMECARE")
        has_tables = page.get("has_tables", False)

        citation_str = f"{doc_name}, " + (
            f"Trang in {printed_page} (PDF Trang {pdf_page})"
            if printed_page
            else f"PDF Trang {pdf_page}"
        )

        # Trường hợp 1: Trang chứa Bảng (Table) -> Giữ nguyên vẹn bảng để không làm vỡ phân liều thuốc
        if has_tables:
            headings = page.get("headings", [])
            sec_title = headings[0] if headings else f"Bảng dữ liệu Trang {pdf_page}"
            
            chunk_obj = {
                "chunk_id": f"CHK-{doc_tag.upper()}-P{pdf_page:02d}-01",
                "content": content,
                "metadata": {
                    "page_index": page_idx,
                    "pdf_page": pdf_page,
                    "printed_page": printed_page,
                    "document_tag": doc_tag,
                    "document_name": doc_name,
                    "knowledge_store": k_store,
                    "safety_tier": safety_tier,
                    "section_title": sec_title,
                    "has_table": True,
                    "char_count": len(content),
                    "citation": citation_str
                }
            }
            chunks.append(chunk_obj)
            continue

        # Trường hợp 2: Trang văn bản thông thường vừa vặn (<= max_chunk_chars)
        if len(content) <= max_chunk_chars:
            headings = page.get("headings", [])
            sec_title = headings[0] if headings else f"Nội dung Trang {pdf_page}"
            
            chunk_obj = {
                "chunk_id": f"CHK-{doc_tag.upper()}-P{pdf_page:02d}-01",
                "content": content,
                "metadata": {
                    "page_index": page_idx,
                    "pdf_page": pdf_page,
                    "printed_page": printed_page,
                    "document_tag": doc_tag,
                    "document_name": doc_name,
                    "knowledge_store": k_store,
                    "safety_tier": safety_tier,
                    "section_title": sec_title,
                    "has_table": False,
                    "char_count": len(content),
                    "citation": citation_str
                }
            }
            chunks.append(chunk_obj)
            continue

        # Trường hợp 3: Trang văn bản dài (> max_chunk_chars), chia nhỏ theo khối ngữ nghĩa
        blocks = split_text_into_semantic_blocks(content)
        current_chunk_parts = []
        current_len = 0
        sub_idx = 1
        current_heading = page.get("headings", ["Nội dung chung"])[0] if page.get("headings") else "Nội dung chung"

        for b in blocks:
            # Nhận diện tiêu đề mới
            if b.startswith("#"):
                clean_h = re.sub(r'^#+\s*', '', b).strip()
                if clean_h:
                    current_heading = clean_h
            elif re.match(r'^\d+(\.\d+)+\s+', b):
                match_h = re.match(r'^(\d+(\.\d+)+\.?\s+[^\n]+)', b)
                if match_h:
                    current_heading = match_h.group(1).strip()

            # Nếu cộng dồn khối mới làm vượt quá max_chunk_chars -> đóng gói chunk hiện tại
            if current_len + len(b) > max_chunk_chars and current_chunk_parts:
                chunk_text = "\n\n".join(current_chunk_parts).strip()
                if len(chunk_text) >= min_chunk_chars:
                    chunk_obj = {
                        "chunk_id": f"CHK-{doc_tag.upper()}-P{pdf_page:02d}-{sub_idx:02d}",
                        "content": chunk_text,
                        "metadata": {
                            "page_index": page_idx,
                            "pdf_page": pdf_page,
                            "printed_page": printed_page,
                            "document_tag": doc_tag,
                            "document_name": doc_name,
                            "knowledge_store": k_store,
                            "safety_tier": safety_tier,
                            "section_title": current_heading,
                            "has_table": False,
                            "char_count": len(chunk_text),
                            "citation": citation_str
                        }
                    }
                    chunks.append(chunk_obj)
                    sub_idx += 1
                current_chunk_parts = [b]
                current_len = len(b)
            else:
                current_chunk_parts.append(b)
                current_len += len(b)

        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts).strip()
            if len(chunk_text) >= min_chunk_chars:
                chunk_obj = {
                    "chunk_id": f"CHK-{doc_tag.upper()}-P{pdf_page:02d}-{sub_idx:02d}",
                    "content": chunk_text,
                    "metadata": {
                        "page_index": page_idx,
                        "pdf_page": pdf_page,
                        "printed_page": printed_page,
                        "document_tag": doc_tag,
                        "document_name": doc_name,
                        "knowledge_store": k_store,
                        "safety_tier": safety_tier,
                        "section_title": current_heading,
                        "has_table": False,
                        "char_count": len(chunk_text),
                        "citation": citation_str
                    }
                }
                chunks.append(chunk_obj)

    return chunks
