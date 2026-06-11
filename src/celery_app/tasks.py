import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete

from celery_app.worker import celery_app
from database import ActivationTokenModel, PasswordResetTokenModel
from database.session import get_postgresql_db_contextmanager
from database.session import engine


@celery_app.task
def delete_expired_tokens():
    asyncio.run(_delete_expired_tokens())


async def _delete_expired_tokens():
    try:
        async with get_postgresql_db_contextmanager() as db:
            now = datetime.now(timezone.utc)

            await db.execute(
                delete(ActivationTokenModel).where(
                    ActivationTokenModel.expires_at < now
                )
            )
            await db.execute(
                delete(PasswordResetTokenModel).where(
                    PasswordResetTokenModel.expires_at < now
                )
            )
            await db.commit()
    finally:
        await engine.dispose()
