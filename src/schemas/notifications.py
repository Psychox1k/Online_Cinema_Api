from datetime import datetime

from pydantic import BaseModel


class NotificationSchema(BaseModel):
    id: int
    to_user: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}