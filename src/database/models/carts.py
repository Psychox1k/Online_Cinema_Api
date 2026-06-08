from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

if TYPE_CHECKING:
    from database import UserModel
    from database import MovieModel


class CartModel(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="cart")
    items: Mapped[list["CartItemModel"]] = relationship(
        "CartItemModel", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CartModel(id={self.id}, user_id={self.user_id})>"


class CartItemModel(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    cart: Mapped["CartModel"] = relationship("CartModel", back_populates="items")
    movie: Mapped["MovieModel"] = relationship("MovieModel")

    __table_args__ = (UniqueConstraint("movie_id", "cart_id"),)

    def __repr__(self):
        return (
            f"<CartItemModel(id={self.id}, cart_id={self.cart_id},"
            f" movie_id={self.movie_id})>"
        )
