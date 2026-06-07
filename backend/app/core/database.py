"""
Database — SQLAlchemy async (PostgreSQL prod / SQLite dev)
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os

def _build_db_url() -> str:
    url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./brvm_analyzer.db").strip()
    # Normalise les variantes Railway/Heroku → driver asyncpg
    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    url = url.replace("postgres://", "postgresql+asyncpg://")
    return url

DATABASE_URL = _build_db_url()

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
