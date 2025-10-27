from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Create a top-level comment
class CommentCreate(BaseModel):
    post_id: str = Field(..., description="ID of the post being commented on")
    content: str = Field(..., description="Text content of the comment")
    user_id: str = Field(..., description="User ID of the commenter")
    image_url: Optional[str] = Field(default=None, description="Optional image URL from Cloudinary")

# Create a reply to a comment
class ReplyCreate(BaseModel):
    post_id: str = Field(..., description="ID of the post")
    parent_comment_id: str = Field(..., description="ID of the comment being replied to")
    content: str = Field(..., description="Text content of the reply")
    user_id: str = Field(..., description="User ID of the replier")
    image_url: Optional[str] = Field(default=None, description="Optional image URL from Cloudinary")

# Update comment or reply
class CommentUpdate(BaseModel):
    content: Optional[str] = Field(None, description="Updated text content")
    image_url: Optional[str] = Field(None, description="Updated image URL")

# Reply response
class ReplyResponse(BaseModel):
    reply_id: str
    content: str
    created_at: datetime
    username: str
    user_id: str
    image_url: Optional[str] = None
    profile_picture: Optional[str] = None

# Comment response with nested replies
class CommentResponse(BaseModel):
    comment_id: str
    post_id: str
    content: str
    created_at: datetime
    username: str
    user_id: str
    image_url: Optional[str] = None
    profile_picture: Optional[str] = None
    replies: Optional[List[ReplyResponse]] = []
