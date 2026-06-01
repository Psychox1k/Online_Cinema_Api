import enum
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List


from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy import (
    ForeignKey,
    String,
    Boolean,
    DateTime,
    Enum,
    Integer,
    func,
    Text,
    Date,
    UniqueConstraint
)

from database.validators import accounts as validators
from security.passwords import hash_password, verify_password
from security.utils import generate_secure_token

from database import Base

class UserGroupEnum(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class GenderEnum(str, enum.Enum):
    MAN = "man"
    WOMAN = "woman"

class UserGroupModel(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )
    users: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        back_populates="group"
    )

    def __repr__(self):
        return f"<UserGroupModel(id={self.id}, name={self.name})>"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )
    _hashed_password: Mapped[str] = mapped_column(
        "hashed_password", String(255),
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    group_id: Mapped[int] = mapped_column(
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        nullable=False
    )
    group: Mapped["UserGroupModel"] = relationship(
        "UserGroupModel",
        back_populates="users"
    )

    activation_token: Mapped[Optional["ActivationTokenModel"]] = relationship(
        "ActivationTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    password_reset_token: Mapped[Optional["PasswordResetTokenModel"]] = relationship(
        "PasswordResetTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    profile: Mapped[Optional["UserProfileModel"]] = relationship(
        "UserProfileModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    likes: Mapped[list["MovieLikesModel"]] = relationship(
        "MovieLikesModel",
        back_populates="user"
    )
    ratings: Mapped[list["MovieRatingModel"]] = relationship(
        "MovieRatingModel",
        back_populates="user"
    )
    comment_likes: Mapped[list["CommentLikeModel"]] = relationship(
        "CommentLikeModel",
        back_populates="user"
    )
    comments: Mapped[list["CommentModel"]] = relationship(
        "CommentModel",
        back_populates="user"
    )
    favorites: Mapped[list["MovieFavoriteModel"]] = relationship(
        "MovieFavoriteModel",
        back_populates="user"
    )

    cart: Mapped[list["CartModel"]] = relationship(
        "CartModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    notifications: Mapped[list["NotificationModel"]] = relationship(
        "NotificationModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    orders: Mapped[list["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserModel(id={self.id}, email={self.email}, is_active={self.is_active})>"

    def has_group(self, group_name: UserGroupEnum) -> bool:
        return self.group.name == group_name

    @classmethod
    def create(cls, email: str, raw_password: str, group_id: int | Mapped[int]) -> "UserModel":
        user = cls(email=email, group_id=group_id)
        user.password = raw_password
        return user

    @property
    def password(self) -> None:
        raise AttributeError("Password is write-only")

    @password.setter
    def password(self, raw_password: str) -> None:
        validators.validate_password_strength(raw_password)
        self._hashed_password = hash_password(raw_password)

    def verify_password(self, raw_password: str) -> bool:
        return verify_password(raw_password, self._hashed_password)

    @validates("email")
    def validate_email(self, key, value):
        return validators.validate_email(value.lower())

class UserProfileModel(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    avatar: Mapped[Optional[str]] = mapped_column(String(255))
    gender: Mapped[Optional["GenderEnum"]] = mapped_column(Enum(GenderEnum))
    date_of_birth: Mapped[datetime] = mapped_column(Date)
    info: Mapped[Text] = mapped_column(Text)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="profile")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return (
            f"<UserProfileModel(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, "
            f"gender={self.gender}, date_of_birth={self.date_of_birth})>"
        )



class TokenBaseModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        default=generate_secure_token
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=1)
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)


class ActivationTokenModel(TokenBaseModel):
    __tablename__ = "activation_tokens"

    user: Mapped[UserModel] = relationship("UserModel", back_populates="activation_token")

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<ActivationTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class PasswordResetTokenModel(TokenBaseModel):
    __tablename__ = "password_reset_tokens"

    user: Mapped[UserModel] = relationship("UserModel", back_populates="password_reset_token")

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<PasswordResetTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


class RefreshTokenModel(TokenBaseModel):
    __tablename__ = "refresh_tokens"

    user: Mapped[UserModel] = relationship("UserModel", back_populates="refresh_tokens")
    token: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        default=generate_secure_token
    )

    @classmethod
    def create(cls, user_id: int | Mapped[int], days_valid: int, token: str) -> "RefreshTokenModel":
        """
        Factory method to create a new RefreshTokenModel instance.

        This method simplifies the creation of a new refresh token by calculating
        the expiration date based on the provided number of valid days and setting
        the required attributes.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=days_valid)
        return cls(user_id=user_id, expires_at=expires_at, token=token)

    __table_args__ = (UniqueConstraint("user_id"),)

    def __repr__(self):
        return f"<RefreshTokenModel(id={self.id}, token={self.token}, expires_at={self.expires_at})>"


