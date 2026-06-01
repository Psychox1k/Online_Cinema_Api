from datetime import datetime

from pydantic import BaseModel, field_validator, ConfigDict
from uuid import UUID
from decimal import Decimal
from typing import Optional, Any, Self

from validation import validate_imdb, validate_year, validate_price


# ===== CERTIFICATION =====
class CertificationSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

# ===== GENRE =====
class GenreBaseSchema(BaseModel):
    name: str

class GenreCreateSchema(GenreBaseSchema):
    pass

class GenreUpdateSchema(BaseModel):
    name: Optional[str] = None

class GenreResponseSchema(GenreBaseSchema):
    id: int
    model_config = ConfigDict(from_attributes=True)
class GenreWithMovieCountSchema(BaseModel):
    id: int
    name: str
    movie_count: int
    model_config = ConfigDict(from_attributes=True)

# ===== STAR =====
class StarBaseSchema(BaseModel):
    name: str

class StarCreateSchema(StarBaseSchema):
    pass

class StarUpdateSchema(BaseModel):
    name: Optional[str] = None

class StarResponseSchema(StarBaseSchema):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ===== DIRECTOR =====
class DirectorBaseSchema(BaseModel):
    name: str

class DirectorCreateSchema(DirectorBaseSchema):
    pass

class DirectorUpdateSchema(BaseModel):
    name: Optional[str] = None

class DirectorResponseSchema(DirectorBaseSchema):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ===== MOVIE =====
class MovieBaseSchema(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: Decimal
    certification_id: int

    @field_validator("year")
    @classmethod
    def validate_year_field(cls, value):
        return validate_year(value)

    @field_validator("price")
    @classmethod
    def validate_price(cls, value):
        return validate_price(value)

    @field_validator("imdb")
    @classmethod
    def validate_imdb_field(cls, value):
        return validate_imdb(value)


class MovieCreateSchema(MovieBaseSchema):
    genres: list[int] = []
    directors: list[int] = []
    stars: list[int] = []


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    year: Optional[int] = None
    time: Optional[int] = None
    imdb: Optional[float] = None
    votes: Optional[int] = None
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    certification_id: Optional[int] = None
    genre: Optional[list[int]] = None
    director: Optional[list[int]] = None
    star: Optional[list[int]] = None

    @field_validator("year")
    @classmethod
    def validate_year_field(cls, value):
        return validate_year(value)

    @field_validator("price")
    @classmethod
    def validate_price(cls, value):
        return validate_price(value)

    @field_validator("imdb")
    @classmethod
    def validate_imdb_field(cls, value):
        return validate_imdb(value)


class MovieListSchema(BaseModel):
    id: int
    name: str
    year: int
    imdb: float
    price: Decimal
    genres: list[GenreResponseSchema] = []
    certification: Optional[CertificationSchema] = None

    model_config = ConfigDict(from_attributes=True)

class MovieDetailSchema(BaseModel):
    id: int
    uuid: UUID
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: Optional[float] = None
    gross: Optional[float] = None
    description: str
    price: Decimal
    certification: Optional[CertificationSchema] = None
    genres: list[GenreResponseSchema] = []
    directors: list[DirectorResponseSchema] = []
    stars: list[StarResponseSchema] = []
    likes_count: int = 0
    dislikes_count: int = 0
    comments_count: int = 0
    favorites_count: int = 0
    average_rating: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

# ===== LIKES =====
class MovieLikeSchema(BaseModel):
    is_like: bool

class MovieLikeResponseSchema(BaseModel):
    message: str

# ===== RATING =====
class MovieRatingSchema(BaseModel):
    rating: int

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        if value < 1 or value > 10:
            raise ValueError("Rating must be between 1 and 10")
        return value

class MovieRatingResponseSchema(BaseModel):
    message: str

# ===== FAVORITES =====
class FavoriteResponseSchema(BaseModel):
    id: int
    movie: MovieListSchema
    model_config = ConfigDict(from_attributes=True)

# ===== COMMENTS =====
class CommentCreateSchema(BaseModel):
    text: str
    parent_id: Optional[int] = None

class CommentUpdateSchema(BaseModel):
    text: str

class CommentResponseSchema(BaseModel):
    id: int
    text: str
    user_id: int
    movie_id: int
    parent_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
# ===== COMMENTS =====

class PaginatedMoviesSchema(BaseModel):
    items: list[MovieListSchema]
    total: int
    page: int
    per_page:int
    total_pages: int
