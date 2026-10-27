from typing import List, Dict, Any, Optional
from backend.app.core.database import get_db_connection
from backend.app.core.config import settings
from pipeline.embedder_bge_m3 import BGEM3Embedder

class PgVectorStore:
    """Tương tác cơ sở dữ liệu PgVector (Load toàn bộ Corpus & Dense Search)."""

    def __init__(self):
        self.table_name = settings.PGVECTOR_TABLE_NAME
        self.embedder = BGEM3Embedder()

    def fetch_all_chunks(self) -> List[Dict[str, Any]]:
        """Lấy toàn bộ 192 chunks metadata từ cơ sở dữ liệu để cache in-memory."""
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                sql = f"""
                SELECT chunk_id, content, section_title, citation, safety_tier,
                       knowledge_store, document_tag, document_name, pdf_page
                FROM {self.table_name};
                """
                cur.execute(sql)
                rows = cur.fetchall()

                chunks = []
                for r in rows:
                    chunks.append({
                        "chunk_id": r[0],
                        "content": r[1],
                        "section_title": r[2],
                        "citation": r[3],
                        "safety_tier": r[4],
                        "knowledge_store": r[5],
                        "document_tag": r[6],
                        "document_name": r[7],
                        "pdf_page": r[8],
                    })
                return chunks
        finally:
            conn.close()

    def search_dense(
        self, query: str, store_filter: Optional[str] = None, candidate_k: int = 15
    ) -> List[Dict[str, Any]]:
        """Truy xuất Dense Vector tương đồng cosine từ PgVector."""
        query_vector = self.embedder.embed_text(query)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                where_clauses = []
                params = [query_vector]

                if store_filter and store_filter != "ALL":
                    where_clauses.append("knowledge_store = %s")
                    params.append(store_filter)

                where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
                params.append(query_vector)
                params.append(candidate_k)

                sql = f"""
                SELECT chunk_id, 1 - (embedding <=> %s::vector) AS similarity_score
                FROM {self.table_name}
                {where_sql}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()
                return [{"chunk_id": r[0], "similarity_score": float(r[1])} for r in rows]
        finally:
            conn.close()
