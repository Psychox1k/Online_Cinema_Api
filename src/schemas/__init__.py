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
    TokenRefreshResponseSchema
)
