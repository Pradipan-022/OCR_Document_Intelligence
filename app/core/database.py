import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Database URL pointing to a local SQLite file
# To swap to PostgreSQL in production, change this string to:
# "postgresql://user:password@localhost:5432/ocr_db"
SQLALCHEMY_DATABASE_URL = "sqlite:///./ocr_platform.db"

#Create database engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    #check same thread is only required for SQLite
    connect_args={"check_same_thread": False} 
    if "sqlite" in SQLALCHEMY_DATABASE_URL 
    else {}
)

#Create a configured session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Create a Base class for ORM models to inherit from
Base = declarative_base()

# 4. Dependency to get DB session per FastAPI HTTP request
def get_db() -> Generator:
    """Creates a fresh database session for a single request,
    and ensures the session closes after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()