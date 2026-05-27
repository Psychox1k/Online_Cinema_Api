import decimal
from datetime import datetime
from typing import Optional

import uuid as uuid_lib
from uuid import UUID as PythonUUID

from sqlalchemy import (
    String,
    Float,
    Text,
    UniqueConstraint,
    ForeignKey,
    Table,
    Column,
    UUID,
    Numeric,
    Integer,
    DateTime,
    func,
    CheckConstraint,
    Boolean
)
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database import Base

MoviesGenresModel = Table(
    "movies_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True,  nullable=False
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)

MoviesStarsModel = Table(
    "movies_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False
    ),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)

MoviesDirectorsModel = Table(
    "movies_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False
    ),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
)

class CertificationModel(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        back_populates="certification"
    )

    def __repr__(self):
        return f"<Certification (name='{self.name}')>"



class StarModel(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Star (name='{self.name}')>"

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesStarsModel,
        back_populates="stars"
    )

class DirectorModel(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesDirectorsModel,
        back_populates="directors"
    )

    def __repr__(self):
        return f"<Director (name='{self.name}')>"


class GenreModel(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["MovieModel"]] = relationship(
        "MovieModel",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __repr__(self):
        return f"<Genre (name='{self.name}')>"

class MovieModel(Base):
    __tablename__ =  "movies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_lib.uuid4,
        unique=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[decimal.Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id"),
        nullable=False
    )

    certification: Mapped["CertificationModel"] = relationship(
        "CertificationModel",
        back_populates="movies"
    )

    directors: Mapped[list["DirectorModel"]] = relationship(
        "DirectorModel",
        secondary=MoviesDirectorsModel,
        back_populates="movies"
    )

    stars: Mapped[list["StarModel"]] = relationship(
        "StarModel",
        secondary=MoviesStarsModel,
        back_populates="movies"
    )

    genres: Mapped[list["GenreModel"]] = relationship(
        "GenreModel",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )

    likes: Mapped[list["MovieLikesModel"]] = relationship(
        "MovieLikesModel",
        back_populates="movie"
    )
    ratings: Mapped[list["MovieRatingModel"]] = relationship(
        "MovieRatingModel",
        back_populates="movie"
    )

    comments: Mapped[list["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="movie"
    )

    favorites: Mapped[list["MovieFavoriteModel"]] = relationship(
        "MovieFavoriteModel",
        back_populates="movie"
    )

    @classmethod
    def default_order_by(cls):
        return [cls.id.desc()]

    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="unique_movie_constraint"),
    )

    def __repr__(self):
        return f"<Movie (name='{self.name}')>"


class MovieLikesModel(Base):
    __tablename__ = "movie_likes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="likes")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="likes")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id"),
    )

class MovieRatingModel(Base):
    __tablename__ = "movie_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="ratings")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id"),
        CheckConstraint("rating >= 1 AND rating <= 10", name="rating_range")
    )

class MovieFavoriteModel(Base):
    __tablename__ = "movie_favorites"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="favorites")
    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id"),
    )



class CommentModel(Base):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False
    )
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True
    )
    comment_likes: Mapped[list["CommentLikeModel"]] = relationship(
        "CommentLikeModel",
        back_populates="comment"
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    movie: Mapped["MovieModel"] = relationship("MovieModel", back_populates="comments")
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comments")


class CommentLikeModel(Base):
    __tablename__ = "comment_likes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False
    )
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="comment_likes"
    )
    comment: Mapped["CommentModel"] = relationship(
        "CommentModel", back_populates="comment_likes"
    )