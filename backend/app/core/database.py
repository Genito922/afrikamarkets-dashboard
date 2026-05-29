"""
Database — SQLAlchemy async (PostgreSQL prod / SQLite dev)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

DATABASE_URL = (
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./brvm_analyzer.db")
    .replace("postgresql://", "postgresql+asyncpg://")
)

engine = create_async_engine(DATABASE_URL, poolclass=NullPool, echo=False)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    from backend.app.models.models import Base
    from backend.app.models import market_models  # enregistre les tables marché  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
