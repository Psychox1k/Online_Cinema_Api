import decimal
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from database import OrderStatusEnum


class OrderMovieSchema(BaseModel):
    id: int
    name: str
    year: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderItemSchema(BaseModel):
    id: int
    movie_id: int
    movie: OrderMovieSchema
    price_at_order: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderSchema(BaseModel):
    id: int
    user_id: int
    created_at: datetime
    status: OrderStatusEnum
    total_amount: Decimal
    items: list[OrderItemSchema]

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdateSchema(BaseModel):
    status: OrderStatusEnum