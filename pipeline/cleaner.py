"""
Text cleaner module for medical RAG markdown documents.
Làm sạch văn bản Markdown y khoa: loại bỏ mục lục, thẻ HTML, comment rác và số trang.
"""

import re

def clean_rag_markdown(text: str) -> str:
    """
    Dọn dẹp văn bản Markdown y khoa để đưa vào pipeline RAG:
    1. Cắt bỏ phần bìa hành chính và Mục lục ở đầu.
    2. Cắt bỏ phần Tài liệu tham khảo ở cuối.
    3. Xóa các thẻ HTML rác (<mark>, <u>, <br>, <b>, <i>, <strong>, <em>...).
    4. Xóa các block comment hình ảnh của PyMuPDF.
    5. Xóa các dòng chỉ chứa số trang đứng riêng lẻ.
    6. Chuẩn hóa khoảng cách dòng trống thừa.
    """
    if not text:
        return ""

    # 1. Tìm vị trí bắt đầu nội dung y khoa thực sự
    start_keyword = "1. ĐỊNH NGHĨA HEN PHẾ QUẢN"
    start_idx = text.find(start_keyword)
    if start_idx != -1:
        text = text[start_idx:]

    # 2. Cắt bỏ phần Tài liệu tham khảo ở cuối
    end_keyword = "TÀI LIỆU THAM KHẢO"
    end_idx = text.rfind(end_keyword)
    if end_idx != -1:
        text = text[:end_idx]

    # 3. Xóa các thẻ HTML rác
    text = re.sub(r'</?(mark|u|br|b|i|strong|em)[^>]*>', '', text, flags=re.IGNORECASE)

    # 4. Xóa các block comment hình ảnh của PyMuPDF
    text = re.sub(r'<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->', '', text, flags=re.DOTALL)

    # 5. Xóa các dòng chỉ chứa số trang đứng riêng lẻ
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)

    # 6. Dọn dẹp dòng trống thừa
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

