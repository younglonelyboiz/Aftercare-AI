import json
import re

def compact_vector_json_string(dataset: list) -> str:
    json_str = json.dumps(dataset, ensure_ascii=False, indent=2)
    compact_json = re.sub(
        r'("embedding_vector":\s*)\[(.*?)\]', 
        lambda m: m.group(1) + '[' + re.sub(r'\s+', '', m.group(2)).replace(',', ', ') + ']', 
        json_str, 
        flags=re.DOTALL
    )
    return compact_json

def compact_vector_in_existing_json(input_json_path: str, output_json_path: str):
    with open(input_json_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    compact_str = compact_vector_json_string(dataset)
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        f.write(compact_str)