import json
import re

def compact_vector_in_existing_json(input_filepath: str, output_filepath: str):
    print(f"Đang đọc dữ liệu từ: {input_filepath}...")
    
    # 1. Đọc file JSON đã tạo
    with open(input_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Đã tải {len(data)} bản ghi. Đang tiến hành ép dòng vector...")

    # 2. Chuyển lại thành chuỗi văn bản với cấu trúc thụt lề 
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    compact_json = re.sub(
        r'("embedding_vector":\s*)\[(.*?)\]', 
        lambda m: m.group(1) + '[' + re.sub(r'\s+', '', m.group(2)).replace(',', ', ') + ']', 
        json_str, 
        flags=re.DOTALL
    )

    # 4. Ghi ra file mới
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(compact_json)
        
    print(f"done!")

if __name__ == "__main__":
    input_file = r"D:\Aftercare-AI\Data\rag_knowledge_base_asthma.json"
    output_file = r"rag_knowledge_base_asthma_compact.json" 
    
    compact_vector_in_existing_json(input_file, output_file)