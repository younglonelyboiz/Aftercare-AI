import json
import uuid
import re
import os
import google.generativeai as genai
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_text_splitters import MarkdownHeaderTextSplitter 

# 1. API LLM

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 2. HÀM DỌN DẸP VĂN BẢN (PRE-PROCESSING)

def clean_rag_markdown(text: str) -> str:
    """Cắt bỏ Mục lục, Từ viết tắt và dọn dẹp khoảng trắng thừa."""
    # Tìm vị trí bắt đầu nội dung y khoa thực sự
    start_keyword = "1. ĐỊNH NGHĨA HEN PHẾ QUẢN"
    start_idx = text.find(start_keyword)
    if start_idx != -1:
        text = text[start_idx:]
        
    # Tìm và cắt bỏ phần Tài liệu tham khảo ở cuối
    end_keyword = "TÀI LIỆU THAM KHẢO"
    end_idx = text.rfind(end_keyword)
    if end_idx != -1:
        text = text[:end_idx]

    # Xóa các dòng trống liên tiếp
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# 3. ĐỊNH NGHĨA SCHEMA va GỌI GEMINI API

class LLMExtractedMetadata(BaseModel):
    topic_category: str = Field(description="Phân loại chủ đề, vd: medication, emergency_signs, lifestyle, action_plan")
    target_audience: str = Field(description="Đối tượng đọc, vd: patient_caregiver, clinician")
    safety_classification: str = Field(description="Phân loại an toàn, vd: EDUCATIONAL_SAFE, RED_FLAG_THRESHOLD, YELLOW_FLAG")

def generate_llm_metadata(content: str) -> dict:
    """Dùng Gemini 3.8 Flash để tự động gán nhãn siêu dữ liệu."""
    model = genai.GenerativeModel('models/gemini-3.8-flash')
    prompt = f"Phân loại đoạn văn bản y khoa sau và trả về JSON chuẩn xác:\n\n{content}"
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=LLMExtractedMetadata,
                temperature=0.1,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Lỗi khi lấy metadata: {e}")
        return {
            "topic_category": "unknown", 
            "target_audience": "unknown", 
            "safety_classification": "UNKNOWN"
        }

def generate_embedding(content: str) -> List[float]:
    """Dùng mô hình gemini-embedding-2 để tạo vector."""
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-2",
            content=content,
            task_type="retrieval_document",
            title="Knowledge Base Chunk"
        )
        return result['embedding']
    except Exception as e:
        print(f"Lỗi khi tạo vector: {e}")
        return []

# 4. QUY TRÌNH XỬ LÝ CHÍNH 

def process_markdown_file_to_rag_json(input_md_path: str, output_json_path: str):
    print(f"Đang đọc file: {input_md_path}...")
    with open(input_md_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    # 1: Dọn dẹp văn bản thô
    clean_text = clean_rag_markdown(raw_text)

    # 2: Phân mảnh ngữ nghĩa dựa vào thẻ Heading
    headers_to_split_on = [
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    
    doc_chunks = markdown_splitter.split_text(clean_text)
    print(f"Đã cắt thành {len(doc_chunks)} chunks ngữ nghĩa. Đang xử lý qua Gemini API...")

    final_dataset: List[Dict[str, Any]] = []

    # 3: Lặp qua từng đoạn để tạo Vector và Metadata
    for idx, chunk in enumerate(doc_chunks):
        content = chunk.page_content.strip()
        if not content or len(content) < 20: # Bỏ qua các đoạn quá ngắn
            continue
            
        print(f"Đang xử lý chunk {idx + 1}/{len(doc_chunks)}...")
        header_metadata = chunk.metadata
        
        # Lấy tiêu đề phần làm tag trích dẫn
        section_title = header_metadata.get("Header_3") or header_metadata.get("Header_2") or header_metadata.get("Header_1") or "Thông tin chung"
        citation_tag = f"[BYT-QĐ1851: {section_title.strip()}]"

        # Gọi API
        llm_meta = generate_llm_metadata(content)
        embedding_vec = generate_embedding(content)

        # Đóng gói JSON 
        chunk_record = {
            "chunk_id": f"CHK-ASTHMA-{str(uuid.uuid4())[:8].upper()}",
            "document_reference": "BYT-QĐ1851",
            "content": content,
            "embedding_vector": embedding_vec,
            "metadata": {
                "source_authority": "Bộ Y tế Việt Nam",
                "clinical_domain": "asthma_management",
                "topic_category": llm_meta.get("topic_category", "unknown"),
                "target_audience": llm_meta.get("target_audience", "unknown"),
                "safety_classification": llm_meta.get("safety_classification", "UNKNOWN"),
                "citation_tag": citation_tag
            }
        }
        final_dataset.append(chunk_record)

    # 4: Lưu kết quả
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)

    print(f"\nHoàn tất! Đã lưu {len(final_dataset)} bản ghi RAG vào: {output_json_path}")


# CHAY NGAY DI
if __name__ == "__main__":
    input_markdown = "D:\Aftercare-AI\Data\hen_phe_quan.md"
    output_json = "rag_knowledge_base_asthma.json"
    
    process_markdown_file_to_rag_json(input_markdown, output_json)