from fastapi import APIRouter, status, HTTPException
from fastapi.params import Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_user
from database import get_db, UserModel, NotificationModel
from schemas import NotificationSchema

router = APIRouter()


@router.get(
    "/",
    response_model=list[NotificationSchema],
    status_code=status.HTTP_200_OK,
    summary="Get user notifications",
    description="Retrieve a list of all notifications for the currently"
    " authenticated user. Sorted by newest first.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {"example": {"detail": "Not authenticated"}}
            },
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": ("An error occurred while" " fetching notifications.")
                    }
                }
            },
        },
    },
)
async def get_user_notifcations(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> list[NotificationSchema]:
    try:
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == current_user.id)
            .order_by(NotificationModel.created_at.desc())
        )

        result = await db.execute(stmt)
        return result.scalars().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching notifications.",
        )
