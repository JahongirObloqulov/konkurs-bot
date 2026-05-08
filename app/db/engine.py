import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base


def create_engine(db_url: str):
    if db_url.startswith("sqlite"):
        os.makedirs("data", exist_ok=True)
    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if db_url.startswith("sqlite"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def create_session_pool(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)