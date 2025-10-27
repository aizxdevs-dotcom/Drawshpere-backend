from fastapi import HTTPException
from app.db import get_db
from app.models.notification import NotificationResponse
from datetime import datetime
from neo4j.time import DateTime


def neo4j_datetime_to_python(neo_dt):
    if isinstance(neo_dt, datetime):
        return neo_dt
    if isinstance(neo_dt, DateTime):
        return neo_dt.to_native()
    return None


def create_notification(user_id: str, actor_id: str, notification_type: str, post_id: str = None, comment_id: str = None):
    """Create a notification for a user"""
    db = get_db()
    
    # Don't create notification if user is reacting to their own content
    if user_id == actor_id:
        return None
    
    # Get actor details
    actor_query = """
    MATCH (u:User {user_id: $actor_id})
    RETURN u.username AS username, u.profile_picture AS profile_picture
    """
    actor_result = db.execute_query(actor_query, {"actor_id": actor_id}, database_="neo4j")
    actor_records = actor_result[0] if actor_result and len(actor_result) > 0 else []
    
    if not actor_records:
        return None
    
    actor = actor_records[0]
    actor_username = actor.get("username", "Someone")
    actor_profile = actor.get("profile_picture")
    
    # Create message based on type
    messages = {
        "like": f"{actor_username} liked your post",
        "love": f"{actor_username} loved your post",
        "haha": f"{actor_username} reacted 😆 to your post",
        "care": f"{actor_username} reacted ❤️ to your post",
        "comment": f"{actor_username} commented on your post",
        "reply": f"{actor_username} replied to your comment"
    }
    message = messages.get(notification_type, f"{actor_username} interacted with your content")
    
    query = """
    MATCH (u:User {user_id: $user_id})
    CREATE (u)-[:HAS_NOTIFICATION]->(n:Notification {
        id: randomUUID(),
        actor_id: $actor_id,
        type: $type,
        post_id: $post_id,
        comment_id: $comment_id,
        message: $message,
        is_read: false,
        created_at: datetime()
    })
    RETURN n
    """
    
    try:
        result = db.execute_query(
            query,
            {
                "user_id": user_id,
                "actor_id": actor_id,
                "type": notification_type,
                "post_id": post_id,
                "comment_id": comment_id,
                "message": message
            },
            database_="neo4j"
        )
        return result
    except Exception as e:
        print(f"⚠️ Error creating notification: {e}")
        return None


def get_user_notifications(user_id: str, limit: int = 20):
    """Get notifications for a user"""
    db = get_db()
    
    query = """
    MATCH (u:User {user_id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification)
    MATCH (actor:User {user_id: n.actor_id})
    RETURN n, actor.username AS actor_username, actor.profile_picture AS actor_profile_picture
    ORDER BY n.created_at DESC
    LIMIT $limit
    """
    
    try:
        result = db.execute_query(query, {"user_id": user_id, "limit": limit}, database_="neo4j")
        records = result[0] if result and len(result) > 0 else []
        
        notifications = []
        for record in records:
            n = record["n"]
            notifications.append(NotificationResponse(
                notification_id=n["id"],
                user_id=user_id,
                actor_id=n["actor_id"],
                actor_username=record.get("actor_username", "Unknown"),
                actor_profile_picture=record.get("actor_profile_picture"),
                type=n["type"],
                post_id=n.get("post_id"),
                comment_id=n.get("comment_id"),
                message=n["message"],
                is_read=n.get("is_read", False),
                created_at=neo4j_datetime_to_python(n["created_at"])
            ))
        
        return {"notifications": notifications, "unread_count": sum(1 for n in notifications if not n.is_read)}
    
    except Exception as e:
        print(f"⚠️ Error getting notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def mark_notification_read(notification_id: str, user_id: str):
    """Mark a notification as read"""
    db = get_db()
    
    query = """
    MATCH (u:User {user_id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification {id: $notification_id})
    SET n.is_read = true
    RETURN n
    """
    
    try:
        result = db.execute_query(query, {"user_id": user_id, "notification_id": notification_id}, database_="neo4j")
        records = result[0] if result and len(result) > 0 else []
        
        if not records:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {"message": "Notification marked as read"}
    
    except Exception as e:
        print(f"⚠️ Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def mark_all_notifications_read(user_id: str):
    """Mark all notifications as read for a user"""
    db = get_db()
    
    query = """
    MATCH (u:User {user_id: $user_id})-[:HAS_NOTIFICATION]->(n:Notification)
    WHERE n.is_read = false
    SET n.is_read = true
    RETURN COUNT(n) AS count
    """
    
    try:
        result = db.execute_query(query, {"user_id": user_id}, database_="neo4j")
        records = result[0] if result and len(result) > 0 else []
        count = records[0].get("count", 0) if records else 0
        
        return {"message": f"Marked {count} notifications as read"}
    
    except Exception as e:
        print(f"⚠️ Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail=str(e))
