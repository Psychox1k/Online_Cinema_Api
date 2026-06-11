from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from schemas import GenreResponseSchema


class CartMovieSchema(BaseModel):
    id: int
    name: str
    price: Decimal
    year: int
    genres: list[GenreResponseSchema] = []

    model_config = ConfigDict(from_attributes=True)


class CartItemSchema(BaseModel):
    id: int
    movie_id: int
    added_at: datetime
    movie: CartMovieSchema
    model_config = ConfigDict(from_attributes=True)


class CartSchema(BaseModel):
    id: int
    items: list[CartItemSchema]
    total_price: Decimal = 0

    model_config = ConfigDict(from_attributes=True)
