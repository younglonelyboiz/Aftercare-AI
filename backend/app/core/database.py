import psycopg2
from pgvector.psycopg2 import register_vector
from backend.app.core.config import settings

def get_db_connection():
    """Tạo kết nối tới PostgreSQL với extension pgvector."""
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD
    )
    register_vector(conn)
    return conn
