import os
from functools import lru_cache
from typing import Iterator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")


# Create engine with some good defaults for PostgreSQL
@lru_cache
def get_engine():
    return create_engine(
        DATABASE_URL,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Enables connection pool "pre-ping" feature
        pool_size=5,  # Maximum number of permanent connections
        max_overflow=10,  # Maximum number of additional connections
    )


# Create all tables on startup
def create_db_and_tables():
    SQLModel.metadata.create_all(get_engine())


# Session dependency
def get_db() -> Iterator[Session]:
    with Session(get_engine()) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
