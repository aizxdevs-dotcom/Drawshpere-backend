from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Model for creating a new post
class PostCreate(BaseModel):
    content: str = Field(..., description="Text content of the post")
    user_id: str = Field(..., description="User ID or reference to the author")
    image_url: Optional[str] = Field(default=None, description="Optional image URL from Cloudinary")
 

# Model for responding to a post request (what client sees)
class PostResponse(BaseModel):
    post_id: str
    content: str
    created_at: datetime
    username: str
    user_id: Optional[str] = None         # For reference if needed
    image_url: Optional[str] = None
    profile_picture: Optional[str] = None


# Model for updating an existing post
class PostUpdate(BaseModel):
    content: Optional[str] = Field(default=None, description="Updated post content")
    image_url: Optional[str] = Field(default=None, description="Updated image URL")
  
