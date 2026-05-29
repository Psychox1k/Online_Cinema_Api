from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from schemas import GenreResponseSchema


class CartItemSchema(BaseModel):
    id: int
    movie_id: int
    movie_name: str
    price: Decimal
    year: int
    genres: list[GenreResponseSchema] = []
    added_at: datetime
    model_config = {"from_attributes": True}

class CartSchema(BaseModel):
    id: int
    items: list[CartItemSchema]
    total_price: Decimal = 0
    model_config = {"from_attributes": True}