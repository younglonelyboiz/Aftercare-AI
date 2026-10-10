"""
JSON Formatter module for RAG knowledge base.
Chuẩn hóa và nén định dạng vector embedding thành 1 dòng duy nhất trong file JSON.
"""

import json
import re
from pathlib import Path
from typing import Union, List, Dict, Any

def compact_vector_json_string(data: List[Dict[str, Any]]) -> str:
    """
    Chuyển danh sách dữ liệu RAG thành JSON string với vector nằm trên một dòng gọn gàng.
    """
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    compact_json = re.sub(
        r'("embedding_vector":\s*)\[(.*?)\]',
        lambda m: m.group(1) + '[' + re.sub(r'\s+', '', m.group(2)).replace(',', ', ') + ']',
        json_str,
        flags=re.DOTALL
    )
    return compact_json

def compact_vector_in_existing_json(
    input_filepath: Union[str, Path],
    output_filepath: Union[str, Path]
):
    """
    Đọc file JSON đã tạo, ép dòng các vector embedding và ghi ra file mới.
    """
    in_path = Path(input_filepath)
    out_path = Path(output_filepath)

    if not in_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file JSON nguồn: {in_path}")

    print(f"[Step 3] Đang đọc dữ liệu từ: {in_path}...")
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[Step 3] Đã tải {len(data)} bản ghi. Đang nén dòng vector...")
    compact_content = compact_vector_json_string(data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compact_content)

    print(f"[Step 3] Thành công! Đã lưu file chuẩn hóa tại: {out_path}")

