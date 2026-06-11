from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.settings import settings

DbSessionGenerator = AsyncGenerator[AsyncSession, None]

engine = create_async_engine(settings.database_url, echo=False)

AsyncSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an asynchronous database session.

    This function returns an async generator yielding a new database session.
    It ensures that the session is properly closed after use.

    :return: An asynchronous generator yielding an AsyncSession instance.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_postgresql_db_contextmanager() -> DbSessionGenerator:
    """
    Provide an asynchronous database session using a context manager.

    This function allows for managing the database session
    within a `with` statement. It ensures that the session is properly
    initialized and closed after execution.

    :return: An asynchronous generator yielding an AsyncSession instance.
    """
    async with AsyncSessionLocal() as session:
        yield session
