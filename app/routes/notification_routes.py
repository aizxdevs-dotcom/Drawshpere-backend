from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_user
from app.controllers import notification_controller

router = APIRouter(tags=["Notifications"])


@router.get("/", status_code=status.HTTP_200_OK)
def get_notifications(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get notifications for current user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return notification_controller.get_user_notifications(current_user["user_id"], limit)


@router.put("/{notification_id}/read", status_code=status.HTTP_200_OK)
def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark a notification as read"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return notification_controller.mark_notification_read(notification_id, current_user["user_id"])


@router.put("/read-all", status_code=status.HTTP_200_OK)
def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark all notifications as read"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return notification_controller.mark_all_notifications_read(current_user["user_id"])
