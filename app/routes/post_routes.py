from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form,
    UploadFile,
    File
)
from typing import Optional

from app.models.post import PostCreate, PostUpdate
from app.controllers import post_controller
from app.auth import get_current_user

router = APIRouter(tags=["Posts"])


# ============================================
# ✅ CREATE POST (Authenticated)
# ============================================
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    ✅ Create a post (authenticated users only).
    Supports optional image upload.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return await post_controller.create_post(content, image, current_user)


# ============================================
# ✅ GET ALL POSTS (Public)
# ============================================
@router.get("/", status_code=status.HTTP_200_OK)
def get_all_posts():
    """✅ Get all posts (public access)."""
    return post_controller.get_all_posts()


# ============================================
# ✅ GET POST BY ID (Authenticated)
# ============================================
@router.get("/{post_id}", status_code=status.HTTP_200_OK)
def get_post_by_id(
    post_id: str,
    current_user: dict = Depends(get_current_user)
):
    """✅ Get a single post by ID (requires authentication)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return post_controller.get_post_by_id(post_id)


# ============================================
# ✅ UPDATE POST (Authenticated + Ownership Check)
# ============================================
@router.put("/{post_id}", status_code=status.HTTP_200_OK)
async def update_post(
    post_id: str,
    content: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    ✅ Update post (authenticated & must own the post).
    Supports optional image update.
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return await post_controller.update_post(post_id, content, image, current_user)


# ============================================
# ✅ DELETE POST (Authenticated + Ownership Check)
# ============================================
@router.delete("/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(
    post_id: str,
    current_user: dict = Depends(get_current_user)
):
    """✅ Delete a post by ID (authenticated & must own the post)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    return post_controller.delete_post(post_id, current_user)
