"""
PostgreSQL pgvector Ingestion Pipeline for Aftercare-AI.
- Kết nối PostgreSQL qua psycopg2.
- Tự động kích hoạt extension 'vector'.
- Tạo bảng 'medical_knowledge_chunks' với cột embedding vector(1024).
- Xây dựng chỉ mục HNSW (Hierarchical Navigable Small World) theo Cosine Distance (vector_cosine_ops).
- Dùng BAAI/bge-m3 để nhúng toàn bộ 192 chunks và nạp dữ liệu cùng đầy đủ siêu dữ liệu (metadata).
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch
from pgvector.psycopg2 import register_vector

BASE_DIR = Path(__file__).resolve().parent.parent

try:
    from pipeline.embedder_bge_m3 import BGEM3Embedder
except ImportError:
    from .embedder_bge_m3 import BGEM3Embedder

load_dotenv()

# Cấu hình kết nối DB từ .env (hoặc giá trị mặc định)
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
DB_NAME = os.getenv("POSTGRES_DB", "aftercare_ai")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

TABLE_NAME = "medical_knowledge_chunks"
CHUNKS_FILE = BASE_DIR / "Data" / "rag_chunks_with_page_index.json"
EMBEDDED_CHUNKS_FILE = BASE_DIR / "Data" / "embedded_rag_chunks_bge_m3.json"

def get_connection():
    """Tạo kết nối tới PostgreSQL."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    register_vector(conn)
    return conn

def setup_database_schema(conn):
    """Bật extension pgvector, tạo bảng và chỉ mục HNSW."""
    with conn.cursor() as cur:
        print("1. Kiểm tra và kích hoạt extension pgvector...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        print(f"2. Tạo bảng '{TABLE_NAME}' (nếu chưa có)...")
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            chunk_id VARCHAR(64) UNIQUE NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1024),
            page_index INT,
            pdf_page INT,
            printed_page INT,
            document_tag VARCHAR(50),
            document_name TEXT,
            knowledge_store VARCHAR(64),
            safety_tier VARCHAR(64),
            section_title TEXT,
            has_table BOOLEAN,
            char_count INT,
            citation TEXT,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_table_query)

        print(f"3. Xây dựng chỉ mục HNSW cosine distance (vector_cosine_ops)...")
        create_index_query = f"""
        CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_hnsw_embedding 
        ON {TABLE_NAME} USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64);
        """
        cur.execute(create_index_query)

        # Index phụ để filter nhanh theo kho và an toàn
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_kstore ON {TABLE_NAME} (knowledge_store);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_safety ON {TABLE_NAME} (safety_tier);")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_doctag ON {TABLE_NAME} (document_tag);")

    conn.commit()
    print("✓ Thiết lập cấu trúc cơ sở dữ liệu và chỉ mục HNSW hoàn tất!")

def ingest_chunks_to_pgvector(batch_size: int = 32):
    """Nạp dữ liệu vào pgvector. Ưu tiên đọc từ embedded_rag_chunks_bge_m3.json nếu đã có sẵn."""
    if EMBEDDED_CHUNKS_FILE.exists():
        print(f"\n--- TÌM THẤY DỮ LIỆU VECTOR ĐÃ ĐƯỢC NHÚNG SẴN ---")
        print(f"Đọc trực tiếp từ: {EMBEDDED_CHUNKS_FILE}")
        with open(EMBEDDED_CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        vectors = [c["embedding_vector"] for c in chunks]
        total_chunks = len(chunks)
    else:
        if not CHUNKS_FILE.exists():
            raise FileNotFoundError(f"Không tìm thấy file dữ liệu chunks tại: {CHUNKS_FILE}")

        print(f"\n--- BẮT ĐẦU QUÁ TRÌNH NHÚNG VÀ INGEST VÀO PGVECTOR ---")
        print(f"Đọc dữ liệu từ: {CHUNKS_FILE}")
        with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        total_chunks = len(chunks)
        print(f"Tổng số chunks cần nhúng: {total_chunks}")
        embedder = BGEM3Embedder()
        texts = [c["content"] for c in chunks]
        vectors = embedder.embed_batch(texts, batch_size=4, show_progress_bar=True)

    # 3. Kết nối DB và nạp dữ liệu
    conn = get_connection()
    try:
        setup_database_schema(conn)

        print(f"\n4. Nạp dữ liệu vào bảng '{TABLE_NAME}'...")
        insert_query = f"""
        INSERT INTO {TABLE_NAME} (
            chunk_id, content, embedding, page_index, pdf_page, printed_page,
            document_tag, document_name, knowledge_store, safety_tier,
            section_title, has_table, char_count, citation, metadata
        ) VALUES (
            %(chunk_id)s, %(content)s, %(embedding)s, %(page_index)s, %(pdf_page)s, %(printed_page)s,
            %(document_tag)s, %(document_name)s, %(knowledge_store)s, %(safety_tier)s,
            %(section_title)s, %(has_table)s, %(char_count)s, %(citation)s, %(metadata)s
        )
        ON CONFLICT (chunk_id) DO UPDATE SET
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            page_index = EXCLUDED.page_index,
            pdf_page = EXCLUDED.pdf_page,
            printed_page = EXCLUDED.printed_page,
            document_tag = EXCLUDED.document_tag,
            document_name = EXCLUDED.document_name,
            knowledge_store = EXCLUDED.knowledge_store,
            safety_tier = EXCLUDED.safety_tier,
            section_title = EXCLUDED.section_title,
            has_table = EXCLUDED.has_table,
            char_count = EXCLUDED.char_count,
            citation = EXCLUDED.citation,
            metadata = EXCLUDED.metadata;
        """

        records = []
        for c, vec in zip(chunks, vectors):
            meta = c.get("metadata", {})
            records.append({
                "chunk_id": c["chunk_id"],
                "content": c["content"],
                "embedding": vec,
                "page_index": meta.get("page_index"),
                "pdf_page": meta.get("pdf_page"),
                "printed_page": meta.get("printed_page"),
                "document_tag": meta.get("document_tag"),
                "document_name": meta.get("document_name"),
                "knowledge_store": meta.get("knowledge_store"),
                "safety_tier": meta.get("safety_tier"),
                "section_title": meta.get("section_title"),
                "has_table": meta.get("has_table", False),
                "char_count": meta.get("char_count", len(c["content"])),
                "citation": meta.get("citation"),
                "metadata": json.dumps(meta, ensure_ascii=False)
            })

        with conn.cursor() as cur:
            execute_batch(cur, insert_query, records, page_size=batch_size)
        conn.commit()

        print(f"✓ THÀNH CÔNG! Đã nạp toàn bộ {total_chunks} chunks (1024 dims) vào PostgreSQL PgVector!")

        # Kiểm tra xác nhận số bản ghi
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
            count = cur.fetchone()[0]
            print(f"✓ Tổng số bản ghi thực tế trong bảng '{TABLE_NAME}': {count}")

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        ingest_chunks_to_pgvector()
    except Exception as e:
        print(f"[ERROR] Lỗi trong quá trình ingest: {e}")
