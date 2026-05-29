from datetime import datetime

from sqlalchemy import Integer, ForeignKey, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, relationship, mapped_column

from database.models.base import Base

class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="notifications"
    )

    def __repr__(self):
        return f"<NotificationModel(id={self.id}, user_id={self.user_id}, is_read={self.is_read})>"