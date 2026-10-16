import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from google import genai
from google.genai import types

load_dotenv()

class AsthmaRetriever:
    def __init__(
        self, 
        qdrant_path: str = "Data/qdrant_db", 
        collection_name: str = "asthma_knowledge_base",
        embedding_model: str = "models/gemini-embedding-2" 
    ):
        self.client = QdrantClient(path=qdrant_path)
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # Khởi tạo genai Client
        self.ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    def get_query_embedding(self, query: str) -> List[float]:
        """Chuyển câu hỏi của bệnh nhân thành vector chiều chuẩn."""
        response = self.ai_client.models.embed_content(
            model=self.embedding_model,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
        )
        # SDK mới trả về list các đối tượng embedding, trỏ vào values của phần tử đầu tiên
        return response.embeddings[0].values

    def retrieve(self, query: str, top_k: int = 3, topic_filter: str = None) -> List[Dict[str, Any]]:
        # (Giữ nguyên hàm này như cũ của bạn)
        query_vector = self.get_query_embedding(query)

        qdrant_filter = None
        if topic_filter:
            qdrant_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.topic_category",
                        match=models.MatchValue(value=topic_filter)
                    )
                ]
            )

        search_result = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            with_payload=True
        ).points

        results = []
        for hit in search_result:
            payload = hit.payload
            metadata = payload.get("metadata", {})
            results.append({
                "chunk_id": payload.get("chunk_id"),
                "score": round(hit.score, 4),
                "content": payload.get("content", ""),
                "citation_tag": metadata.get("citation_tag", "[Tài liệu Y khoa]"),
                "source_authority": metadata.get("source_authority", "Bộ Y tế"),
                "keywords": metadata.get("extracted_keywords", [])
            })
        return results

    def format_context_for_llm(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        # (Giữ nguyên hàm này như cũ của bạn)
        if not retrieved_docs:
            return "Không tìm thấy tài liệu y khoa đặc thù cho câu hỏi này."
        
        formatted_chunks = []
        for idx, doc in enumerate(retrieved_docs, 1):
            chunk_str = (
                f"--- ĐOẠN TÀI LIỆU #{idx} ---\n"
                f"Mã trích dẫn: {doc['citation_tag']}\n"
                f"Nguồn: {doc['source_authority']}\n"
                f"Nội dung:\n{doc['content']}\n"
            )
            formatted_chunks.append(chunk_str)
        return "\n".join(formatted_chunks)