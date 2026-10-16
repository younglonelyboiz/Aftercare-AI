import json
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct

def ingest_json_to_qdrant(json_filepath: str, collection_name: str, db_path: str):
    print(f"1. Đang khởi tạo Qdrant Database tại thư mục: {db_path}...")
    client = QdrantClient(path=db_path)

    if not client.collection_exists(collection_name=collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
        print(f"   -> Đã tạo mới collection: '{collection_name}' (3072 dimensions).")
    else:
        print(f"   -> Collection '{collection_name}' đã tồn tại.")

    print(f"2. Đang đọc dữ liệu từ: {json_filepath}...")
    with open(json_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("3. Đang chuyển đổi và nạp dữ liệu vào Qdrant...")
    points = []
    for idx, item in enumerate(data):
        payload = {
            "chunk_id": item["chunk_id"],
            "document_reference": item["document_reference"],
            "content": item["content"]
        }
        payload.update(item["metadata"])

        point = PointStruct(
            id=idx, 
            vector=item["embedding_vector"],
            payload=payload
        )
        points.append(point)

    client.upsert(collection_name=collection_name, points=points)
    print(f"\nDone! Đã nạp thành công {len(points)} chunks vào Qdrant Database tại '{db_path}'.")

if __name__ == "__main__":
    INPUT_JSON = r"D:\Aftercare-AI\Data\rag_knowledge_base.json"
    COLLECTION_NAME = "DATN26_medical_guidelines"
    DB_STORAGE_PATH = r"D:\Aftercare-AI\Data\qdrant_db"
    
    ingest_json_to_qdrant(INPUT_JSON, COLLECTION_NAME, DB_STORAGE_PATH)