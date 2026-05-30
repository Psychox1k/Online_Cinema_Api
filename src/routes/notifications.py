from fastapi import APIRouter, status
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_moderator, get_current_user
from database import get_db, UserModel, NotificationModel
from schemas import NotificationSchema

router = APIRouter()

@router.get(
    "/",
    response_model=list[NotificationSchema],
    status_code=status.HTTP_200_OK,
    summary="Get user notifications",
    description="Retrieve a list of all notifications for the currently authenticated moderator or admin. Sorted by newest first."
)
async def get_user_notifcations(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> NotificationSchema:
    stmt = select(NotificationModel).where(
        NotificationModel.user_id == current_user.id
    ).order_by(NotificationModel.created_at.desc())

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return notifications
