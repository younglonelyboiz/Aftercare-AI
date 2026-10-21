from typing import List, Dict, Any
from pipeline.embedder_bge_m3 import BGEM3Embedder
from backend.app.core.database import get_db_connection
from backend.app.core.config import settings

class PgVectorRetriever:
    """Truy vấn tìm kiếm tri thức y khoa dựa trên HNSW Cosine Similarity trong PgVector."""
    def __init__(self):
        self.embedder = BGEM3Embedder()
        self.table_name = settings.PGVECTOR_TABLE_NAME

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        safety_tier_filter: str = None,
        knowledge_store_filter: str = None
    ) -> List[Dict[str, Any]]:
        query_vector = self.embedder.embed_text(query)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                where_clauses = []
                params = [query_vector]

                if safety_tier_filter:
                    where_clauses.append("safety_tier = %s")
                    params.append(safety_tier_filter)

                if knowledge_store_filter:
                    where_clauses.append("knowledge_store = %s")
                    params.append(knowledge_store_filter)

                where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

                params.append(query_vector)
                params.append(top_k)

                sql = f"""
                SELECT chunk_id, content, section_title, citation, safety_tier,
                       knowledge_store, document_tag, document_name, pdf_page,
                       1 - (embedding <=> %s::vector) AS similarity_score
                FROM {self.table_name}
                {where_sql}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

                results = []
                for r in rows:
                    results.append({
                        "chunk_id": r[0],
                        "content": r[1],
                        "section_title": r[2],
                        "citation": r[3],
                        "safety_tier": r[4],
                        "knowledge_store": r[5],
                        "document_tag": r[6],
                        "document_name": r[7],
                        "pdf_page": r[8],
                        "similarity_score": float(r[9])
                    })
                return results
        finally:
            conn.close()
