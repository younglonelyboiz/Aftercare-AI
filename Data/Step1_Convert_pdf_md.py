import pymupdf4llm
import pathlib
import re

def clean_rag_markdown(text: str) -> str:
    #Cắt bỏ toàn bộ phần hành chính và Mục lục ở đầu file
    start_keyword = "1. ĐỊNH NGHĨA HEN PHẾ QUẢN"
    start_idx = text.find(start_keyword)
    if start_idx != -1:
        text = text[start_idx:]
        
    # 2. Cắt bỏ phần Tài liệu tham khảo ở cuối file
    end_keyword = "TÀI LIỆU THAM KHẢO"
    end_idx = text.rfind(end_keyword)
    if end_idx != -1:
        text = text[:end_idx]

    # 3. Xóa các thẻ HTML rác (<mark>, <u>, <br>, <b>, <i>...)
    text = re.sub(r'</?(mark|u|br|b|i|strong|em)[^>]*>', '', text, flags=re.IGNORECASE)
    
    # 4. Xóa các block comment hình ảnh của PyMuPDF
    text = re.sub(r'<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->', '', text, flags=re.DOTALL)
    
    # 5. Xóa các dòng chỉ chứa số trang đứng riêng lẻ
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
    
    # 6. Dọn dẹp dòng trống thừa (chuẩn hóa khoảng cách)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def extract_and_clean_pdf(pdf_path: str, output_md_path: str):
    """
    Trích xuất PDF, dọn dẹp văn bản và lưu thành Markdown chuẩn.
    """
    print(f"Đang xử lý file: {pdf_path}...")
    
    # 1. Trích xuất PDF sang Markdown thô
    raw_markdown = pymupdf4llm.to_markdown(pdf_path)
    
    # 2. Xóa số thứ tự trang và các dòng rác
    clean_markdown = clean_rag_markdown(raw_markdown)
    
    # 3. Ghi file Markdown đã được làm sạch với chuẩn UTF-8
    pathlib.Path(output_md_path).write_bytes(clean_markdown.encode('utf-8'))
    print(f"Đã lưu nội dung Markdown sạch tại: {output_md_path}")
    
    return clean_markdown

if __name__ == "__main__":
    input_pdf = r"D:\Aftercare-AI\Data\Hướng-dẫn-chẩn-đoán-và-điều-trị-Hen-phế-quản-người-lớn-và-trẻ-_12-tuổi.pdf"
    output_md = "hen_phe_quan.md"
    
    final_markdown = extract_and_clean_pdf(
        pdf_path=input_pdf,
        output_md_path=output_md
    )