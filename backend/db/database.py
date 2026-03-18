"""
db/database.py — Async SQLAlchemy engine + session factory
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from core.config import get_settings

settings = get_settings()

# Sync Engine (psycopg2)
engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Session
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# Base class
class Base(DeclarativeBase):
    pass



class Base(DeclarativeBase):
    pass

