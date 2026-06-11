from schemas.movies import (
    # movie
    MovieBaseSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
    MovieListSchema,
    MovieDetailSchema,
    PaginatedMoviesSchema,
    # genre
    GenreBaseSchema,
    GenreCreateSchema,
    GenreUpdateSchema,
    GenreResponseSchema,
    GenreWithMovieCountSchema,
    # star
    StarBaseSchema,
    StarCreateSchema,
    StarUpdateSchema,
    StarResponseSchema,
    # director
    DirectorBaseSchema,
    DirectorCreateSchema,
    DirectorUpdateSchema,
    DirectorResponseSchema,
    # certification
    CertificationSchema,
    # likes
    MovieLikeSchema,
    MovieLikeResponseSchema,
    # rating
    MovieRatingSchema,
    MovieRatingResponseSchema,
    # favorites
    FavoriteResponseSchema,
    # comments
    CommentCreateSchema,
    CommentUpdateSchema,
    CommentResponseSchema,
)
from schemas.accounts import (
    UserRegistrationRequestSchema,
    UserRegistrationResponseSchema,
    UserActivationRequestSchema,
    MessageResponseSchema,
    PasswordResetRequestSchema,
    PasswordResetCompleteSchema,
    UserLoginResponseSchema,
    UserLoginRequestSchema,
    TokenRefreshRequestSchema,
    TokenRefreshResponseSchema,
)

from schemas.notifications import NotificationSchema
from schemas.carts import CartItemSchema, CartSchema

from schemas.orders import (
    OrderMovieSchema,
    OrderItemSchema,
    OrderSchema,
    OrderStatusUpdateSchema,
)

__all__ = [
    "MovieBaseSchema",
    "MovieCreateSchema",
    "MovieUpdateSchema",
    "MovieListSchema",
    "MovieDetailSchema",
    "PaginatedMoviesSchema",
    "GenreBaseSchema",
    "GenreCreateSchema",
    "GenreUpdateSchema",
    "GenreResponseSchema",
    "GenreWithMovieCountSchema",
    "StarBaseSchema",
    "StarCreateSchema",
    "StarUpdateSchema",
    "StarResponseSchema",
    "DirectorBaseSchema",
    "DirectorCreateSchema",
    "DirectorUpdateSchema",
    "DirectorResponseSchema",
    "CertificationSchema",
    "MovieLikeSchema",
    "MovieLikeResponseSchema",
    "MovieRatingSchema",
    "MovieRatingResponseSchema",
    "FavoriteResponseSchema",
    "CommentCreateSchema",
    "CommentUpdateSchema",
    "CommentResponseSchema",
    "UserRegistrationRequestSchema",
    "UserRegistrationResponseSchema",
    "UserActivationRequestSchema",
    "MessageResponseSchema",
    "PasswordResetRequestSchema",
    "PasswordResetCompleteSchema",
    "UserLoginResponseSchema",
    "UserLoginRequestSchema",
    "TokenRefreshRequestSchema",
    "TokenRefreshResponseSchema",
    "NotificationSchema",
    "CartItemSchema",
    "CartSchema",
    "OrderMovieSchema",
    "OrderItemSchema",
    "OrderSchema",
    "OrderStatusUpdateSchema",
]
