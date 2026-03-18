"""
db/database.py — Async SQLAlchemy engine + session factory
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from core.config import get_settings

settings = get_settings()

# Async Engine (using asyncpg)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Async Session
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Base class
class Base(DeclarativeBase):
    pass

# Dependency for FastAPI
async def get_db():
    async with async_session() as session:
        yield session