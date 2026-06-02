from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_moderator, get_current_admin
from database import get_db, DirectorModel, UserModel
from schemas import MessageResponseSchema
from schemas.movies import DirectorCreateSchema, DirectorUpdateSchema, DirectorResponseSchema

router = APIRouter()

@router.get(
    "/",
    response_model=list[DirectorResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all directors",
    description="Retrieve a list of all directors.",
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
async def get_all_directors(
        db: AsyncSession = Depends(get_db)
) -> list[DirectorResponseSchema]:
    try:
        stmt = select(DirectorModel)
        result = await db.execute(stmt)

        return result.scalars().all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching directors."
        )

@router.get(
    "/{director_id}/",
    response_model=DirectorResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get director by ID",
    description="Retrieve a specific director by ID.",
    responses={
        404: {
            "description": "Not Found - Director not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director not found."
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
async def get_director_by_id(
        director_id: int,
        db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(DirectorModel).where(DirectorModel.id == director_id)
        result = await db.execute(stmt)
        director = result.scalar_one_or_none()
        if not director:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Director not found."
            )
        return director

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching director."
        )

@router.post(
    "/",
    response_model=DirectorResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create director",
    description="Create a new director. Only moderators and admins can perform this action.",
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
            "description": "Conflict - Director with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director already exists."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating director."
                    }
                }
            }
        }
    }
)
async def create_director(
    director_data: DirectorCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)
):
    stmt = select(DirectorModel).where(DirectorModel.name == director_data.name)
    result = await db.execute(stmt)
    existing_director = result.scalar_one_or_none()

    if existing_director:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Director already exists."
        )
    try:
        director = DirectorModel(name=director_data.name)
        db.add(director)
        await db.commit()
        await db.refresh(director)
        return director
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating director."
        )

@router.patch(
    "/{director_id}/",
    response_model=DirectorResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update director",
    description="Update a director. Only moderators and admins can perform this action.",
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
            "description": "Not Found - Director not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director not found."
                    }
                }
            }
        },
        409: {
            "description": "Conflict - Director with this name already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Director with this name already exists."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "An error occurred while updating director."}}}
        }
    }
)
async def update_director(
    director_id: int,
    director_data: DirectorUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)

):
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalar_one_or_none()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found."
        )
    try:
        director.name = director_data.name
        await db.commit()
        await db.refresh(director)
        return director

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Director with this name already exists."
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating director."
        )

@router.delete(
    "/{director_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete director",
    description="Delete a director. Only admins can perform this action.",
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
            "description": "Not Found - Director not found.",
            "content": {
                "application/json": {
                    "example": {
                    "detail": "Director not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting director."
                    }
                }
            }
        }
    }
)
async def delete_director(
        director_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    stmt = select(DirectorModel).where(DirectorModel.id == director_id)
    result = await db.execute(stmt)
    director = result.scalar_one_or_none()

    if not director:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Director not found."
        )

    try:
        await db.delete(director)
        await db.commit()
        return MessageResponseSchema(message="director successfully deleted.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting director."
        )