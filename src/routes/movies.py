import math
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, or_, delete
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config.dependencies import get_current_moderator, get_current_admin, get_current_user
from database import get_db, MovieModel, MoviesGenresModel, GenreModel, StarModel, DirectorModel, UserModel, \
    MovieRatingModel, MovieLikesModel, MovieFavoriteModel, CommentModel, CommentLikeModel
from schemas import MovieDetailSchema, MovieCreateSchema, MovieUpdateSchema, MessageResponseSchema, MovieRatingSchema, \
    CommentCreateSchema, CommentUpdateSchema
from schemas.movies import MovieListSchema, PaginatedMoviesSchema, MovieLikeResponseSchema, MovieLikeSchema, \
    MovieRatingResponseSchema, CommentResponseSchema

router = APIRouter()

async def get_movie_stats(movie_id: int, db:AsyncSession) -> dict:
    likes_count = await db.scalar(
        select(func.count(MovieLikesModel)).where(
            MovieLikesModel.movie_id == movie_id,
            MovieLikesModel.is_like == True
        )
    )
    dislikes_count = await db.scalar(
        select(func.count(MovieLikesModel)).where(
            MovieLikesModel.movie_id == movie_id,
            MovieLikesModel.is_like == False
        )
    )

    comments_count = await db.scalar(
        select(func.count(CommentModel)).where(
            CommentModel.movie_id == movie_id
        )
    )
    favorites_count = await db.scalar(
        select(func.count(MovieFavoriteModel)).where(
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
    description="Browse movies with pagination, filtering by year, IMDb rating, price, genre and sorting.",
    responses={
        200: {"description": "Successfully retrieved movie list."},
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

    stmt = select(MovieModel)

    stmt = apply_movie_filters(stmt, search, year, min_imdb, max_imdb, min_price, max_price, genre)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    total_pages = math.ceil(total / per_page)

    stmt = apply_movie_sorting(stmt, sort_by, sort_order)

    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    db_movies = result.scalars().all()

    return PaginatedMoviesSchema(
        items=db_movies,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.post(
    "/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create movie",
    description="Create a new movie. Only moderators and admins can perform this action.",
    responses={
        400: {
            "description": "Bad Request - Movie with this name, year and duration already exists.",
            "content": {"application/json": {"example": {"detail": "Movie already exists."}}}
        },
        403: {
            "description": "Forbidden - Only moderators can perform this action.",
            "content": {"application/json": {"example": {"detail": "Only moderators can perform this action."}}}
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "Database error."}}}
        },
    }
)
async def create_movie(
        movie_data: MovieCreateSchema,
        current_user: UserModel = Depends(get_current_moderator),
        db: AsyncSession = Depends(get_db)

) -> MovieDetailSchema:

    stmt = select(MovieModel).where(
        MovieModel.name == movie_data.name,
        MovieModel.time == movie_data.time,
        MovieModel.year == movie_data.year
    )
    result = await db.execute(stmt)
    existing_movie = result.scalar_one_or_none()

    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie existed"
        )

    try:

        genres = []
        for genre_name in movie_data.genres:
            genre_stmt = select(GenreModel).where(GenreModel.name == genre_name)
            genre_result = await db.execute(genre_stmt)
            genre = genre_result.scalars().first()

            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        stars = []
        for star_name in movie_data.stars:
            star_stmt = select(StarModel).where(StarModel.name == star_name)
            star_result = await db.execute(star_stmt)
            star = star_result.scalars().first()

            if not star:
                star = StarModel(name=star_name)
                db.add(star)
                await db.flush()
            stars.append(star)

        directors = []
        for director_name in movie_data.directors:
            director_stmt = select(DirectorModel).where(DirectorModel.name == director_name)
            director_result = await db.execute(director_stmt)
            director = director_result.scalars().first()

            if not director:
                director = DirectorModel(name=director_name)
                db.add(director)
                await db.flush()
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
            "content": {"application/json": {"example": {"detail": "Movie not found."}}}
        },
    }
)
async def get_movie_by_id(
        movie_id: int,
        db: AsyncSession = Depends(get_db)
) -> MovieDetailSchema:
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)

    db_movie = result.scalars().first()

    if not db_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

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

@router.patch(
    "/{movie_id}/",
    response_model=MovieDetailSchema,
    status_code=status.HTTP_200_OK,
    summary="Update movie",
    description="Update movie details. Only moderators and admins can perform this action.",
    responses={
        404: {
            "description": "Not Found - Movie with this ID does not exist.",
            "content": {"application/json": {"example": {"detail": "Movie not found."}}}
        },
        403: {
            "description": "Forbidden - Only moderators can perform this action.",
            "content": {"application/json": {"example": {"detail": "Only moderators can perform this action."}}}
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "An error occurred while updating movie."}}}
        },
    }
)
async def movie_update(
    movie_id: int,
    movie_data: MovieUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_moderator)
) -> MovieDetailSchema:
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)

    db_movie = result.scalars().first()

    if not db_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )
    try:
        update_data = movie_data.model_dump(exclude_unset=True)

        genres = update_data.pop("genres", None)
        stars = update_data.pop("stars", None)
        directors = update_data.pop("directors", None)

        for field, value in update_data.items():
            setattr(db_movie, field, value)

        if genres is not None:
            genre_objects = []
            for genre_name in genres:
                genre_stmt = select(GenreModel).where(
                    func.lower(GenreModel.name) == genre_name.lower()
                )
                genre_result = await db.execute(genre_stmt)
                genre = genre_result.scalars().first()
                if not genre:
                    genre = GenreModel(name=genre_name)
                    db.add(genre)
                    await db.flush()
                genre_objects.append(genre)
            db_movie.genres = genre_objects

        if directors is not None:
            director_objects = []
            for director_name in directors:
                director_stmt = select(DirectorModel).where(
                    func.lower(DirectorModel.name) == director_name.lower()
                )
                director_result = await db.execute(director_stmt)
                director = director_result.scalars().first()
                if not director:
                    director = DirectorModel(name=director_name)
                    db.add(director)
                    await db.flush()
                director_objects.append(director)
            db_movie.directors = director_objects

        if stars is not None:
            star_objects = []
            for star_name in stars:
                star_stmt = select(StarModel).where(
                    func.lower(StarModel.name) == star_name.lower()
                )
                star_result = await db.execute(star_stmt)
                star = star_result.scalars().first()
                if not star:
                    star = StarModel(name=star_name)
                    db.add(star)
                    await db.flush()
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
    description="Delete a movie. Only admins can perform this action.",
    responses={
        404: {
            "description": "Not Found - Movie with this ID does not exist.",
            "content": {"application/json": {"example": {"detail": "Movie not found."}}}
        },
        403: {
            "description": "Forbidden - Only admins can perform this action.",
            "content": {"application/json": {"example": {"detail": "Only admins can perform this action."}}}
        },
        500: {
            "description": "Internal Server Error.",
            "content": {"application/json": {"example": {"detail": "An error occurred while deleting movie."}}}
        },
    }
)
async def movie_delete(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_admin)
) -> MessageResponseSchema:
    stmt = select(MovieModel).where(MovieModel.id == movie_id)
    result = await db.execute(stmt)

    db_movie = result.scalars().first()

    if not db_movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found"
        )

    try:
        await db.delete(db_movie)
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
)
async def like_movie(
        movie_id: int,
        like_data: MovieLikeSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
) -> MovieLikeResponseSchema:

    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

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
    description="Remove your like or dislike from a movie."
)
async def remove_like(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> MessageResponseSchema:
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

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
)
async def rate_movie(
        movie_id: int,
        rating_data: MovieRatingSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

    stmt = select(MovieRatingModel).where(
        MovieRatingModel.movie_id == movie_id,
        MovieRatingModel.user_id == current_user.id
    )
    result = await db.execute(stmt)
    existing_rating = result.scalar_one_or_none()

    try:
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
)
async def remove_rating(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> MessageResponseSchema:

    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

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

# # ===== FAVORITES =====
@router.get(
    "/favorites/",
    response_model=PaginatedMoviesSchema,
    status_code=status.HTTP_200_OK,
    summary="Get favorite movies",
    description="Get current user's favorite movies with filtering and pagination."
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
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    db_movies = result.scalars().all()

    return PaginatedMoviesSchema(
        items=db_movies,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )

@router.post(
    "/{movie_id}/favorites/",
    response_model=MessageResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add movie to favorites",
    description="Add a movie to your favorites list."
)
async def add_movie_to_favorites(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
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
        return MessageResponseSchema(message="Movie added to favorites successfully.")

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
    description="Remove a movie from your favorites list."
)
async def remove_movie_from_favorites(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
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
        return MessageResponseSchema(message="Movie removed from favorites successfully.")
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
    description="Get all comments for a specific movie."
)
async def get_comments_by_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
    stmt = select(CommentModel).where(
        CommentModel.movie_id == movie_id
    ).order_by(CommentModel.created_at.asc())

    result = await db.execute(stmt)
    comments = result.scalars().all()
    return comments


@router.post(
    "/{movie_id}/comments/",
    response_model=CommentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
    description="Write a comment on a movie."
)
async def create_comment(
    movie_id: int,
    comment_data: CommentCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )
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
    description="Update your comment."
)
async def edit_comment(
    movie_id: int,
    comment_id: int,
    comment_data: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
) -> CommentResponseSchema:
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

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
    description="Delete your comment."
)
async def delete_comment(
    movie_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    movie = await db.get(MovieModel, movie_id)
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found."
        )

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
    description="Like a comment."
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
    description="Remove your like from a comment."
)
async def remove_like_from_comment(
    movie_id: int,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
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
    try:
        await db.delete(existing_like)
        await db.commit()
        return MessageResponseSchema(message="Comment like removed successfully.")
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while removing comment like."
        )