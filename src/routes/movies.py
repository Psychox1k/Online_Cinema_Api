import math
from asyncio import start_unix_server
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, or_, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.status import HTTP_400_BAD_REQUEST

from config.dependencies import (
    get_current_moderator,
    get_current_admin,
    get_current_user,
    get_movie_or_404
)
from database import (
    get_db,
    MovieModel,
    MoviesGenresModel,
    GenreModel,
    StarModel,
    DirectorModel,
    UserModel,
    MovieRatingModel,
    MovieLikesModel,
    MovieFavoriteModel,
    CommentModel,
    CommentLikeModel, UserGroupModel, NotificationModel
)
from database.models.carts import CartItemModel
from schemas import (
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    MessageResponseSchema,
    MovieRatingSchema,
    CommentCreateSchema,
    CommentUpdateSchema
)
from schemas.movies import (
    MovieListSchema,
    PaginatedMoviesSchema,
    MovieLikeResponseSchema,
    MovieLikeSchema,
    MovieRatingResponseSchema,
    CommentResponseSchema
)

router = APIRouter()

async def get_movie_stats(movie_id: int, db:AsyncSession) -> dict:
    likes_count = await db.scalar(
        select(func.count(MovieLikesModel.id)).where(
            MovieLikesModel.movie_id == movie_id,
            MovieLikesModel.is_like == True
        )
    )
    dislikes_count = await db.scalar(
        select(func.count(MovieLikesModel.id)).where(
            MovieLikesModel.movie_id == movie_id,
            MovieLikesModel.is_like == False
        )
    )

    comments_count = await db.scalar(
        select(func.count(CommentModel.id)).where(
            CommentModel.movie_id == movie_id
        )
    )
    favorites_count = await db.scalar(
        select(func.count(MovieFavoriteModel.id)).where(
            MovieFavoriteModel.movie_id == movie_id
        )
    )
    average_rating = await db.scalar(
        select(func.avg(MovieRatingModel.rating)).where(
            MovieRatingModel.movie_id == movie_id
        )
    )

    return {
        "likes_count": likes_count or 0,
        "dislikes_count": dislikes_count or 0,
        "comments_count": comments_count or 0,
        "favorites_count": favorites_count or 0,
        "average_rating": round(average_rating, 1) if average_rating else None
    }


def apply_movie_filters(stmt, search, year, min_imdb, max_imdb, min_price, max_price, genre):
    if search:
        stmt = stmt.outerjoin(MovieModel.stars).outerjoin(MovieModel.directors).where(
            or_(
                MovieModel.name.ilike(f"%{search}%"),
                MovieModel.description.ilike(f"%{search}%"),
                StarModel.name.ilike(f"%{search}%"),
                DirectorModel.name.ilike(f"%{search}%"),
            )
        ).distinct()

    if year:
        stmt = stmt.where(MovieModel.year == year)

    if min_imdb:
        stmt = stmt.where(MovieModel.imdb >= min_imdb)

    if max_imdb:
        stmt = stmt.where(MovieModel.imdb <= max_imdb)

    if min_price:
        stmt = stmt.where(MovieModel.price >= min_price)

    if max_price:
        stmt = stmt.where(MovieModel.price <= max_price)

    if genre:
        stmt = stmt.join(MoviesGenresModel).join(GenreModel).where(
            GenreModel.name == genre
        )

    return stmt

def apply_movie_sorting(stmt, sort_by, sort_order):
    sort_column = getattr(MovieModel, sort_by)
    if sort_order == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    return stmt



@router.get(
    "/",
    response_model=PaginatedMoviesSchema,
    status_code=status.HTTP_200_OK,
    summary="Get movie catalog",
    description="Browse movies with pagination, filtering by year,"
                " IMDb rating, price, genre and sorting.",
    responses={
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching movies."
                    }
                }
            }
        }
    }
)
async def get_all_movies(
        db: AsyncSession = Depends(get_db),
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1, le=100),
        year: Optional[int] = Query(default=None),
        search: Optional[str] = Query(default=None),
        min_imdb: Optional[float] = Query(default=None),
        max_imdb: Optional[float] = Query(default=None),
        min_price: Optional[float] = Query(default=None),
        max_price: Optional[float] = Query(default=None),
        genre: Optional[str] = Query(default=None),
        sort_by: Optional[str] = Query(default="id", enum=["id", "price", "imdb", "year"]),
        sort_order: Optional[str] = Query(default="asc", enum=["asc", "desc"]),
) -> PaginatedMoviesSchema:
    try:
        stmt = select(MovieModel)

        stmt = apply_movie_filters(stmt, search, year, min_imdb, max_imdb, min_price, max_price, genre)

        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        total_pages = math.ceil(total / per_page)

        stmt = apply_movie_sorting(stmt, sort_by, sort_order)

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page).options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.certification),
            selectinload(MovieModel.directors),
            selectinload(MovieModel.stars)
        )

        result = await db.execute(stmt)
        db_movies = result.scalars().all()

        return PaginatedMoviesSchema(
            items=db_movies,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching movies."
        )


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create movie",
    description="Create a new movie. Only moderators and admins can perform"
                " this action.",
    responses={
        409: {
            "description": "Conflict - Movie already exists.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie already exists."
                    }
                }
            }
        },
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
            "description": "Forbidden - Only moderators can perform this action.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only moderators can perform this action."
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
        },
    }
)
async def create_movie(
    movie_data: MovieCreateSchema,
    current_user: UserModel = Depends(get_current_moderator),
    db: AsyncSession = Depends(get_db),
) -> MovieDetailSchema:
    try:
        stmt = select(MovieModel).where(
            MovieModel.name == movie_data.name,
            MovieModel.time == movie_data.time,
            MovieModel.year == movie_data.year
        )
        result = await db.execute(stmt)
        existing_movie = result.scalar_one_or_none()

        if existing_movie:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Movie already exists."
            )

        genres = []
        for genre_id in movie_data.genres:
            genre = await db.get(GenreModel, genre_id)
            if not genre:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Genre with ID {genre_id} not found."
                )
            genres.append(genre)

        stars = []
        for star_id in movie_data.stars:
            star = await db.get(StarModel, star_id)
            if not star:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Star with ID {star_id} not found."
                )
            stars.append(star)

        directors = []
        for director_id in movie_data.directors:
            director = await db.get(DirectorModel, director_id)
            if not director:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Director with ID {director_id} not found."
                )
            directors.append(director)

        movie = MovieModel(
            name=movie_data.name,
            year=movie_data.year,
            time=movie_data.time,
            imdb=movie_data.imdb,
            votes=movie_data.votes,
            meta_score=movie_data.meta_score,
            gross=movie_data.gross,
            description=movie_data.description,
            price=movie_data.price,
            certification_id=movie_data.certification_id,
            genres=genres,
            stars=stars,
            directors=directors
        )

        db.add(movie)
        await db.commit()
        await db.refresh(movie, ["genres", "stars", "directors", "certification"])

        return MovieDetailSchema.model_validate(movie)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Invalid input data.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database error.")



@router.get(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Get movie by ID",
    description="Retrieve detailed information about a specific movie.",
    responses={
        404: {
            "description": "Not Found - Movie with this ID does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching the movie."
                    }
                }
            }
        }
    }
)
async def get_movie_by_id(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    db_movie: MovieModel = Depends(get_movie_or_404)
) -> MovieDetailSchema:
    try:
        stats = await get_movie_stats(movie_id, db)

        return MovieDetailSchema(
            id=db_movie.id,
            uuid=db_movie.uuid,
            name=db_movie.name,
            year=db_movie.year,
            time=db_movie.time,
            imdb=db_movie.imdb,
            votes=db_movie.votes,
            meta_score=db_movie.meta_score,
            gross=db_movie.gross,
            description=db_movie.description,
            price=db_movie.price,
            certification=db_movie.certification,
            genres=db_movie.genres,
            directors=db_movie.directors,
            stars=db_movie.stars,
            **stats
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the movie."
        )

@router.patch(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Update movie",
    description="Update movie details. Only moderators and admins can perform this action.",
    responses={
        404: {
            "description": "Not Found - Movie with this ID does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Only moderators can perform this action.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only moderators can perform this action."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating movie."
                    }
                }
            }
        },
    }
)
async def movie_update(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator),
    db_movie: MovieModel = Depends(get_movie_or_404)
) -> MovieDetailSchema:
    try:
        update_data = movie_data.model_dump(exclude_unset=True)

        genres = update_data.pop("genres", None)
        stars = update_data.pop("stars", None)
        directors = update_data.pop("directors", None)

        for field, value in update_data.items():
            setattr(db_movie, field, value)

        if genres is not None:
            genre_objects = []
            for genre_id in genres:
                genre = await db.get(GenreModel, genre_id)
                if not genre:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Genre with ID {genre_id} not found."
                    )
                genre_objects.append(genre)
            db_movie.genres = genre_objects

        if directors is not None:
            director_objects = []
            for director_id in directors:
                director = await db.get(DirectorModel, director_id)
                if not director:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Director with ID {director_id} not found."
                    )
                director_objects.append(director)
            db_movie.directors = director_objects

        if stars is not None:
            star_objects = []
            for star_id in stars:
                star = await db.get(StarModel, star_id)
                if not star:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Star with ID {star_id} not found."
                    )
                star_objects.append(star)
            db_movie.stars = star_objects

        await db.commit()
        await db.refresh(db_movie, ["genres", "stars", "directors", "certification"])
        return MovieDetailSchema.model_validate(db_movie)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating movie"
        )


@router.delete(
    "/{movie_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete movie",
    description="Delete a movie. Only admins can perform this action."
                " Notifies moderators if the movie was in any user's cart.",
    responses={
        404: {
            "description": "Not Found - Movie with this ID does not exist.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Only admins can perform this action.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only admins can perform this action."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting movie."
                    }
                }
            }
        },
    }
)
async def movie_delete(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin),
    movie: MovieModel = Depends(get_movie_or_404)
) -> MessageResponseSchema:

    count_stmt = select(func.count()).select_from(CartItemModel).where(
        CartItemModel.movie_id == movie_id
    )
    carts_count = await db.scalar(count_stmt)

    try:
        await db.delete(movie)

        if carts_count  and carts_count > 0:
            stmt = select(UserModel).join(UserGroupModel).where(
                UserGroupModel.name.in_(["moderator", "admin"])
            )
            moderators = (await db.execute(stmt)).scalars().all()
            message_text = (f"Admin {current_user.email} deleted movie '{movie.name}' (ID: {movie.id}),"
                            f" which was present in {carts_count} user carts.")
            for mod in moderators:
                db.add(NotificationModel(user_id=mod.id, message=message_text))


        await db.commit()
        return MessageResponseSchema(message="Movie was successfully deleted")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting movie"
        )


# ===== LIKE=====
@router.post(
    "/{movie_id}/like/",
    response_model=MovieLikeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Like or dislike a movie",
    description="Like or dislike a movie. If already liked/disliked — updates the vote.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {"application/json": {"example": {"detail": "Not authenticated"}}}
        },
        404: {
            "description": "Not Found - Movie not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "Movie not found."}}}
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while processing your request."
                    }
                }
            }
        }
    }
)
async def like_movie(
    movie_id: int,
    like_data: MovieLikeSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
) -> MovieLikeResponseSchema:

    stmt = select(MovieLikesModel).where(
        MovieLikesModel.movie_id == movie_id,
        MovieLikesModel.user_id == current_user.id
    )

    result = await db.execute(stmt)
    existing_like = result.scalar_one_or_none()

    try:
        if existing_like:
            existing_like.is_like = like_data.is_like
            action = "updated"
        else:
            new_like = MovieLikesModel(
                movie_id=movie_id,
                user_id=current_user.id,
                is_like=like_data.is_like
            )
            db.add(new_like)
            action = "liked" if like_data.is_like else "disliked"
        await db.commit()
        return MovieLikeResponseSchema(
            message=f"Movie {action} successfully."
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request."
        )


@router.delete(
    "/{movie_id}/like/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove like",
    description="Remove your like or dislike from a movie.",
    responses={
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"}}}
        },
        404: {
            "description": "Not Found - Like or movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You have not liked or disliked this movie."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing like."
                    }
                }
            }
        }
    }
)
async def remove_like(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
) -> MessageResponseSchema:

    stmt = select(MovieLikesModel).where(
        MovieLikesModel.movie_id == movie_id,
        MovieLikesModel.user_id == current_user.id
    )

    result = await db.execute(stmt)
    existing_like = result.scalar_one_or_none()

    if not existing_like:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You have not liked or disliked this movie."
        )

    try:
        await db.delete(existing_like)
        await db.commit()
        return MessageResponseSchema(message="Like removed successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing like."
        )


# # ===== RATE =====
@router.post(
    "/{movie_id}/rate/",
    response_model=MovieRatingResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Rate a movie",
    description="Rate a movie 1-10. If already rated — updates the rating.",
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
        404: {
            "description": "Not Found - Movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while rating movie."
                    }
                }
            }
        }
    }
)
async def rate_movie(
    movie_id: int,
    rating_data: MovieRatingSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
):
    try:
        stmt = select(MovieRatingModel).where(
            MovieRatingModel.movie_id == movie_id,
            MovieRatingModel.user_id == current_user.id
        )
        result = await db.execute(stmt)
        existing_rating = result.scalar_one_or_none()


        if existing_rating:
            existing_rating.rating = rating_data.rating
            message = f"Rating updated to {rating_data.rating}."
        else:
            new_rating = MovieRatingModel(
                movie_id=movie.id,
                user_id=current_user.id,
                rating=rating_data.rating
            )
            db.add(new_rating)
            message = f"Movie rated {rating_data.rating} successfully."

        await db.commit()
        return MovieRatingResponseSchema(message=message)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while rating movie."
        )


@router.delete(
    "/{movie_id}/rate/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove rating",
    description="Remove your rating from a movie.",
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
        404: {
            "description": "Not Found - Rating or movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Rating not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing rating."
                    }
                }
            }
        }
    }
)
async def remove_rating(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
) -> MessageResponseSchema:

    stmt = select(MovieRatingModel).where(
        MovieRatingModel.movie_id == movie_id,
        MovieRatingModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing_rating = result.scalar_one_or_none()

    if not existing_rating:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rating not found."
        )

    try:
        await db.delete(existing_rating)
        await db.commit()
        return MessageResponseSchema(message="Rating removed successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing rating."
        )

# ===== FAVORITES =====
@router.get(
    "/favorites/",
    response_model=PaginatedMoviesSchema,
    status_code=status.HTTP_200_OK,
    summary="Get favorite movies",
    description="Get current user's favorite movies with filtering and"
                " pagination.",
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
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching favorites."
                    }
                }
            }
        }
    }
)
async def get_favorite_movies(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=100),
    year: Optional[int] = Query(default=None),
    search: Optional[str] = Query(default=None),
    min_imdb: Optional[float] = Query(default=None),
    max_imdb: Optional[float] = Query(default=None),
    min_price: Optional[float] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default="id", enum=["id", "price", "imdb", "year"]),
    sort_order: Optional[str] = Query(default="asc", enum=["asc", "desc"]),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PaginatedMoviesSchema:
    try:
        stmt = select(MovieModel).join(
            MovieFavoriteModel,
            MovieFavoriteModel.movie_id == MovieModel.id
        ).where(
            MovieFavoriteModel.user_id == current_user.id
        )

        stmt = apply_movie_filters(
            stmt,
            search,
            year,
            min_imdb,
            max_imdb,
            min_price,
            max_price,
            genre
        )

        total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
        total_pages = math.ceil(total / per_page)

        stmt = apply_movie_sorting(stmt, sort_by, sort_order)

        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page).options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.certification),
            selectinload(MovieModel.stars),
            selectinload(MovieModel.directors)
        )

        result = await db.execute(stmt)
        db_movies = result.scalars().all()

        return PaginatedMoviesSchema(
            items=db_movies,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching favorites."
        )

@router.post(
    "/{movie_id}/favorites/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add movie to favorites",
    description="Add a movie to your favorites list.",
    responses={
        400: {
            "description": "Bad Request - Movie already in favorites.",
            "content": {"application/json": {"example": {"detail": "Movie has already in your favorites."}}}
        },
        401: {
            "description": "Unauthorized - Missing or invalid token.",
            "content": {"application/json": {"example": {"detail": "Not authenticated"}}}
        },
        404: {
            "description": "Not Found - Movie not found.",
            "content": {"application/json": {"example": {"detail": "Movie not found."}}}
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "An error occurred while adding movie to favorites."}}}
        }
    }
)
async def add_movie_to_favorites(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie: MovieModel = Depends(get_movie_or_404)
):
    stmt = select(MovieFavoriteModel).where(
        MovieFavoriteModel.user_id == current_user.id,
        MovieFavoriteModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    db_favorite = result.scalar_one_or_none()

    if db_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie has already in your favorites."
        )
    try:
        favorite = MovieFavoriteModel(
            movie_id=movie_id,
            user_id=current_user.id
        )
        db.add(favorite)
        await db.commit()
        return MessageResponseSchema(
            message="Movie added to favorites successfully."
        )

    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding movie to favorites."
        )


@router.delete(
    "/{movie_id}/favorites/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove movie from favorites",
    description="Remove a movie from your favorites list.",
    responses={
        400: {
            "description": "Bad Request - Movie not in favorites.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie hasn't found in your favorites."
                    }
                }
            }
        },
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
        404: {
            "description": "Not Found - Movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing movie "
                                  "from favorites."
                    }
                }
            }
        }
    }
)
async def remove_movie_from_favorites(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    movie: MovieModel = Depends(get_movie_or_404)
):
    stmt = select(MovieFavoriteModel).where(
        MovieFavoriteModel.user_id == current_user.id,
        MovieFavoriteModel.movie_id == movie_id
    )
    result = await db.execute(stmt)
    db_favorite = result.scalar_one_or_none()

    if not db_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie hasn't found in your favorites."
        )
    try:
        await db.delete(db_favorite)
        await db.commit()
        return MessageResponseSchema(
            message="Movie removed from favorites successfully."
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing movie from favorites."
        )


# # ===== COMMENTS =====
@router.get(
    "/{movie_id}/comments/",
    response_model=list[CommentResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get movie comments",
    description="Get all comments for a specific movie.",
    responses={
        404: {
            "description": "Not Found - Movie not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Movie not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while fetching comments."
                    }
                }
            }
        }
    }
)
async def get_comments_by_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    movie: MovieModel = Depends(get_movie_or_404)
):
    try:
        stmt = select(CommentModel).where(
            CommentModel.movie_id == movie_id
        ).order_by(CommentModel.created_at.asc())

        result = await db.execute(stmt)
        comments = result.scalars().all()
        return comments
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching comments."
        )


@router.post(
    "/{movie_id}/comments/",
    response_model=CommentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
    description="Write a comment on a movie.",
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
        404: {
            "description": "Not Found - Movie or parent comment not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Parent comment not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while creating comment."
                    }
                }
            }
        }
    }
)
async def create_comment(
    movie_id: int,
    comment_data: CommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
):
    if comment_data.parent_id:
        parent = await db.get(CommentModel, comment_data.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found."
            )
    try:
        comment = CommentModel(
            movie_id=movie.id,
            user_id=current_user.id,
            text=comment_data.text,
            parent_id=comment_data.parent_id
        )
        db.add(comment)
        await db.commit()
        await db.refresh(comment)
        return comment
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating comment."
        )


@router.patch(
    "/{movie_id}/comments/{comment_id}/",
    response_model=CommentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update comment",
    description="Update your comment.",
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
        404: {
            "description": "Not Found - Movie or comment not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Comment not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while updating comment."
                    }
                }
            }
        }
    }
)
async def edit_comment(
    movie_id: int,
    comment_id: int,
    comment_data: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    movie: MovieModel = Depends(get_movie_or_404)
) -> CommentResponseSchema:

    stmt = select(CommentModel).where(
        CommentModel.id == comment_id,
        CommentModel.movie_id == movie_id,
        CommentModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    db_comment = result.scalar_one_or_none()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found."
        )
    try:
        db_comment.text = comment_data.text
        await db.commit()
        await db.refresh(db_comment)
        return db_comment
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating comment."
        )


@router.delete(
    "/{movie_id}/comments/{comment_id}/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Delete comment",
    description="Delete your comment.",
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
        404: {
            "description": "Not Found - Movie or comment not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Comment not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while deleting comment."
                    }
                }
            }
        }
    }
)
async def delete_comment(
    movie_id: int,
    comment_id: int,
    movie: MovieModel = Depends(get_movie_or_404),
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    stmt = select(CommentModel).where(
        CommentModel.id == comment_id,
        CommentModel.movie_id == movie_id,
        CommentModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    db_comment = result.scalar_one_or_none()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found."
        )
    try:
        await db.delete(db_comment)
        await db.commit()
        return MessageResponseSchema(message="Comment was deleted successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting comment."
        )

@router.post(
    "/{movie_id}/comments/{comment_id}/like/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Like a comment",
    description="Like a comment.",
    responses={
        400: {
            "description": "Bad Request - Comment already liked.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You have already liked this comment."
                    }
                }
            }
        },
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
        404: {
            "description": "Not Found - Comment not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Comment not found."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while liking comment."
                    }
                }
            }
        }
    }
)
async def like_comment(
    movie_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):

    comment = await db.get(CommentModel, comment_id)
    if not comment or comment.movie_id != movie_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found."
        )

    stmt = select(CommentLikeModel).where(
        CommentLikeModel.comment_id == comment_id,
        CommentLikeModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing_like = result.scalar_one_or_none()

    if existing_like:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already liked this comment."
        )

    try:
        like = CommentLikeModel(
            comment_id=comment_id,
            user_id=current_user.id
        )
        db.add(like)
        await db.commit()
        return MessageResponseSchema(message="Comment liked successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while liking comment."
        )
@router.delete(
    "/{movie_id}/comments/{comment_id}/like/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Remove comment like",
    description="Remove your like from a comment.",
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
        404: {
            "description": "Not Found - Like not found.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "You have not liked this comment."
                    }
                }
            }
        },
        500: {
            "description": "Internal Server Error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "An error occurred while removing comment like."
                    }
                }
            }
        }
    }
)
async def remove_like_from_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        stmt = select(CommentLikeModel).where(
            CommentLikeModel.comment_id == comment_id,
            CommentLikeModel.user_id == current_user.id
        )
        result = await db.execute(stmt)
        existing_like = result.scalar_one_or_none()

        if not existing_like:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You have not liked this comment."
            )

        await db.delete(existing_like)
        await db.commit()
        return MessageResponseSchema(message="Comment like removed successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing comment like."
        )