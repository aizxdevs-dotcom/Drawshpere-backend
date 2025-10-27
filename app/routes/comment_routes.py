from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from typing import Optional
from app.auth import get_current_user
from app.models.comment import CommentCreate, ReplyCreate, CommentUpdate
from app.controllers import comment_controller

router = APIRouter(tags=["Comments"])

# ✅ Create comment
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await comment_controller.create_comment(post_id, content, image, current_user)


# ✅ Create reply
@router.post("/reply", status_code=status.HTTP_201_CREATED)
async def create_reply(
    post_id: str = Form(...),
    parent_comment_id: str = Form(...),
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await comment_controller.create_reply(post_id, parent_comment_id, content, image, current_user)


# ✅ Get comments + replies
@router.get("/{post_id}", status_code=status.HTTP_200_OK)
def get_comments(post_id: str):
    return comment_controller.get_comments(post_id)


# ✅ Update comment/reply
@router.put("/{comment_id}", status_code=status.HTTP_200_OK)
def update_comment(
    comment_id: str,
    content: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    comment_data = CommentUpdate(content=content)
    return comment_controller.update_comment(comment_id, comment_data, current_user)


# ✅ Delete comment/reply
@router.delete("/{comment_id}", status_code=status.HTTP_200_OK)
def delete_comment(comment_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return comment_controller.delete_comment(comment_id, current_user)

