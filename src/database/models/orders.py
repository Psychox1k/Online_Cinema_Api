import decimal
import enum
from datetime import datetime

from sqlalchemy import Integer, ForeignKey, func, DateTime, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class OrderStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    status: Mapped[OrderStatusEnum] = mapped_column(
        Enum(OrderStatusEnum),
        default=OrderStatusEnum.PENDING,
        nullable=False
    )
    total_amount: Mapped[decimal.Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="orders"
    )
    items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<OrderModel(id={self.id}, user_id={self.user_id}, status={self.status})>"

class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey(
            "movies.id",
            ondelete="CASCADE"
        ),
        nullable=False
    )
    price_at_order: Mapped[decimal.Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False
    )

    order: Mapped["OrderModel"] = relationship(
        "OrderModel",
        back_populates="items"
    )
    movie: Mapped["MovieModel"] = relationship(
        "MovieModel",
        back_populates="order_items"
    )

    def __repr__(self):
        return f"<OrderItemModel(id={self.id}, order_id={self.order_id}, movie_id={self.movie_id})>"