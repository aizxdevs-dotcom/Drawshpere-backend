from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    notification_id: str
    user_id: str
    actor_id: str
    actor_username: str
    actor_profile_picture: Optional[str] = None
    type: str  # "like", "love", "haha", "care", "comment", "reply"
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    message: str
    is_read: bool
    created_at: datetime
