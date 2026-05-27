from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_moderator, get_current_admin
from database import get_db, GenreModel, UserModel, MoviesGenresModel
from schemas import MessageResponseSchema, GenreWithMovieCountSchema
from schemas.movies import GenreCreateSchema, GenreUpdateSchema, GenreResponseSchema

router = APIRouter()

@router.get(
    "/",
    response_model=list[GenreWithMovieCountSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all genres",
    description="Retrieve a list of all genres.",
)
async def get_all_genres(
        db: AsyncSession = Depends(get_db)
) -> list[GenreResponseSchema]:

    movie_count_subquery = (
        select(func.count(MoviesGenresModel.c.movie_id)).where(
            MoviesGenresModel.c.genre_id == GenreModel.id
        ).scalar_subquery()
    )

    stmt = select(
        GenreModel,
        movie_count_subquery.label("movie_count")
    )

    result = await db.execute(stmt)

    rows = result.all()

    return [
        GenreWithMovieCountSchema(
            id=row.GenreModel.id,
            name=row.GenreModel.name,
            movie_count=row.movie_count
        )
        for row in rows
    ]

@router.get(
    "/{genre_id}/",
    response_model=GenreResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get genre by ID",
    description="Retrieve a specific genre by ID.",
    responses={
        404: {
            "description": "Not Found - genre not found.",
            "content": {"application/json": {"example": {"detail": "genre not found."}}}
        }
    }
)
async def get_genre_by_id(
        genre_id: int,
        db: AsyncSession = Depends(get_db)
):
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalar_one_or_none()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found."
        )
    return genre


@router.post(
    "/",
    response_model=GenreResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create genre",
    description="Create a new genre. Only moderators and admins can perform this action.",
    responses={
        409: {
            "description": "Conflict - genre with this name already exists.",
            "content": {"application/json": {"example": {"detail": "genre already exists."}}}
        },
        403: {
            "description": "Forbidden.",
            "content": {"application/json": {"example": {"detail": "Only moderators can perform this action."}}}
        },
    }
)
async def create_genre(
    genre_data: GenreCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)
):
    stmt = select(GenreModel).where(GenreModel.name == genre_data.name)
    result = await db.execute(stmt)
    existing_genre = result.scalar_one_or_none()

    if existing_genre:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Genre already exists."
        )
    try:
        genre = GenreModel(name=genre_data.name)
        db.add(genre)
        await db.commit()
        await db.refresh(genre)
        return genre
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating genre."
        )

@router.patch(
    "/{genre_id}/",
    response_model=GenreResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update genre",
    description="Update a genre. Only moderators and admins can perform this action.",
    responses={
        404: {
            "description": "Not Found.",
            "content": {"application/json": {"example": {"detail": "genre not found."}}}
        },
        409: {
            "description": "Conflict - genre with this name already exists.",
            "content": {"application/json": {"example": {"detail": "genre already exists."}}}
        },
    }
)
async def update_genre(
    genre_id: int,
    genre_data: GenreUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)

):
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalar_one_or_none()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found."
        )
    try:
        genre.name = genre_data.name
        await db.commit()
        await db.refresh(genre)
        return genre

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Genre with this name already exists."
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating genre."
        )

@router.delete(
    "/{genre_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete genre",
    description="Delete a genre. Only moderators and admins can perform this action.",
    responses={
        404: {
            "description": "Not Found.",
            "content": {"application/json": {"example": {"detail": "genre not found."}}}
        },
    }
)
async def delete_genre(
        genre_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_admin)
):
    stmt = select(GenreModel).where(GenreModel.id == genre_id)
    result = await db.execute(stmt)
    genre = result.scalar_one_or_none()

    if not genre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Genre not found."
        )

    try:
        await db.delete(genre)
        await db.commit()
        return MessageResponseSchema(message="Genre successfully deleted.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting genre."
        )