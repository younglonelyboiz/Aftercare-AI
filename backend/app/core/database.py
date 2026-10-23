import psycopg2
from pgvector.psycopg2 import register_vector
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# 1. Kết nối truyền thống psycopg2 (phục vụ RAG / seed vector nếu cần)
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

# 2. Cấu hình SQLAlchemy 2.0 ORM
SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency cung cấp Session DB cho FastAPI Controllers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
