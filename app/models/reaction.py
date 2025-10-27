from pydantic import BaseModel
from datetime import datetime

class ReactionCreate(BaseModel):
    post_id: str
    type: str  # e.g., "like", "love", "haha", etc.


class ReactionResponse(BaseModel):
    reaction_id: str
    user_id: str
    username: str
    post_id: str
    type: str
    created_at: datetime
