from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings


engine = create_async_engine(settings.database_url, echo=False)

AsyncSessionLocal = sessionmaker(  # type: ignore
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

