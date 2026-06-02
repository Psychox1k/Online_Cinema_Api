from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_moderator, get_current_admin
from database import get_db, StarModel, UserModel
from schemas import MessageResponseSchema
from schemas.movies import (
    StarCreateSchema,
    StarUpdateSchema,
    StarResponseSchema
)

router = APIRouter()


@router.get(
    "/",
    response_model=list[StarResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all stars",
    description="Retrieve a list of all stars.",
    responses={
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Database error."
                    }
                }
            }
        }
    }
)
async def get_all_stars(
        db: AsyncSession = Depends(get_db)
) -> list[StarResponseSchema]:
    try:
        stmt = select(StarModel)
        result = await db.execute(stmt)
        return result.scalars().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching stars."
        )


@router.get(
    "/{star_id}/",
    response_model=StarResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get star by ID",
    description="Retrieve a specific star by ID.",
    responses={
        404: {
            "description": "Not Found - Star not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Database error."
                    }
                }
            }
        }
    }
)
async def get_star_by_id(
        star_id: int,
        db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(StarModel).where(StarModel.id == star_id)
        result = await db.execute(stmt)
        star = result.scalar_one_or_none()

        if not star:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Star not found."
            )
        return star
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching star."
        )


@router.post(
    "/",
    response_model=StarResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create star",
    description="Create a new star. Only moderators and admins can perform"
                " this action.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Insufficient permissions.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only moderators can perform this action."
                    }
                }
            }
        },
        409: {
            "description": "Conflict - Star with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star already exists."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating star."
                    }
                }
            }
        }
    }
)
async def create_star(
    star_data: StarCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)
):
    stmt = select(StarModel).where(StarModel.name == star_data.name)
    result = await db.execute(stmt)
    existing_star = result.scalar_one_or_none()

    if existing_star:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Star already exists."
        )
    try:
        star = StarModel(name=star_data.name)
        db.add(star)
        await db.commit()
        await db.refresh(star)
        return star
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating star."
        )

@router.patch(
    "/{star_id}/",
    response_model=StarResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update star",
    description="Update a star. Only moderators and admins"
                " can perform this action.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Insufficient permissions.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only moderators can perform this action."
                    }
                }
            }
        },
        404: {
            "description": "Not Found - Star not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found."
                    }
                }
            }
        },
        409: {
            "description": "Conflict - Star with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star with this name already exists."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating star."
                    }
                }
            }
        }
    }
)
async def update_star(
    star_id: int,
    star_data: StarUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)
):
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalar_one_or_none()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found."
        )
    try:
        star.name = star_data.name
        await db.commit()
        await db.refresh(star)
        return star
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Star with this name already exists."
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating star."
        )

@router.delete(
    "/{star_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete star",
    description="Delete a star. Only admins can perform this action.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Insufficient permissions.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only admins can perform this action."
                    }
                }
            }
        },
        404: {
            "description": "Not Found - Star not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Star not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting star."
                    }
                }
            }
        }
    }
)
async def delete_star(
        star_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    stmt = select(StarModel).where(StarModel.id == star_id)
    result = await db.execute(stmt)
    star = result.scalar_one_or_none()

    if not star:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Star not found."
        )

    try:
        await db.delete(star)
        await db.commit()
        return MessageResponseSchema(message="Star successfully deleted.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting star."
        )