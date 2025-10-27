from fastapi import HTTPException, UploadFile
from app.db import get_db
from app.models.comment import CommentCreate, ReplyCreate, CommentUpdate, CommentResponse, ReplyResponse
from app.cloudinary_util import upload_image
from app.controllers import notification_controller
from datetime import datetime
from neo4j.time import DateTime
from typing import Optional

# Convert Neo4j datetime to Python datetime
def neo4j_datetime_to_python(neo_dt):
    if isinstance(neo_dt, datetime):
        return neo_dt  # already Python datetime
    if isinstance(neo_dt, DateTime):
        return neo_dt.to_native()  # convert Neo4j datetime to Python datetime
    return None

# Create top-level comment
async def create_comment(post_id: str, content: str, image: Optional[UploadFile], current_user: dict):
    db = get_db()
    
    # Get post author for notification
    post_query = """
    MATCH (p:Post {id: $post_id})<-[:CREATED]-(author:User)
    RETURN author.user_id AS author_id
    """
    post_result = db.execute_query(post_query, {"post_id": post_id}, database_="neo4j")
    post_records = post_result[0] if post_result and len(post_result) > 0 else []
    author_id = post_records[0].get("author_id") if post_records else None
    
    # Upload image if provided
    image_url = None
    if image:
        result = await upload_image(image, folder="drawsphere/comments")
        image_url = result["url"]
    
    query = """
    MATCH (u:User {user_id: $user_id}), (p:Post {id: $post_id})
    CREATE (u)-[:COMMENTED]->(c:Comment {
        id: randomUUID(),
        content: $content,
        image_url: $image_url,
        created_at: datetime(),
        author_id: $user_id
    })-[:ON]->(p)
    RETURN c, u.username AS username, u.user_id AS user_id, u.profile_picture AS profile_picture
    """
    params = {
        "user_id": current_user["user_id"],
        "post_id": post_id,
        "content": content,
        "image_url": image_url
    }

    try:
        result = db.execute_query(query, params, database_="neo4j")

        # Handle EagerResult or list of records
        records = getattr(result, "records", result)
        if not records or len(records) == 0:
            raise HTTPException(status_code=500, detail="Failed to create comment")

        record = records[0]  # first record
        # Access record fields
        if hasattr(record, "get"):  # Neo4j Record
            c = record.get("c")
            username = record.get("username", current_user.get("username", "Unknown"))
            user_id = record.get("user_id", current_user["user_id"])
            profile_picture = record.get("profile_picture")
        else:  # fallback for dict/tuple
            c = record[0]
            username = current_user.get("username", "Unknown")
            user_id = current_user["user_id"]
            profile_picture = None

        if not c:
            raise HTTPException(status_code=500, detail="Failed to create comment node")

        # Convert datetime to Python datetime
        created_at = neo4j_datetime_to_python(c.get("created_at"))
        
        # Create notification for post author
        if author_id:
            notification_controller.create_notification(
                user_id=author_id,
                actor_id=current_user["user_id"],
                notification_type="comment",
                post_id=post_id,
                comment_id=c["id"]
            )

        return CommentResponse(
            comment_id=c["id"],
            post_id=post_id,
            content=c["content"],
            created_at=created_at,
            username=username,
            user_id=user_id,
            image_url=c.get("image_url"),
            profile_picture=profile_picture,
            replies=[]  # new comment has no replies yet
        )

    except Exception as e:
        print(f"⚠️ Error in create_comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Create reply
async def create_reply(post_id: str, parent_comment_id: str, content: str, image: Optional[UploadFile], current_user: dict):
    db = get_db()
    
    # Upload image if provided
    image_url = None
    if image:
        result = await upload_image(image, folder="drawsphere/comments")
        image_url = result["url"]
    
    query = """
    MATCH (u:User {user_id: $user_id}), (p:Post {id: $post_id}), (parent:Comment {id: $parent_comment_id})
    CREATE (u)-[:COMMENTED]->(c:Comment {
        id: randomUUID(),
        content: $content,
        image_url: $image_url,
        created_at: datetime(),
        author_id: $user_id
    })-[:ON]->(p)
    CREATE (c)-[:REPLIED_TO]->(parent)
    RETURN c, u.username AS username, u.user_id AS user_id, u.profile_picture AS profile_picture
    """
    params = {
        "user_id": current_user["user_id"],
        "post_id": post_id,
        "content": content,
        "parent_comment_id": parent_comment_id,
        "image_url": image_url
    }

    try:
        result = db.execute_query(query, params, database_="neo4j")

        # Handle both dict or list return
        records = result.get("records", []) if isinstance(result, dict) else result
        if not records:
            raise HTTPException(status_code=500, detail="Failed to create reply — no records returned")

        record = records[0]
        if isinstance(record, dict):
            r = record.get("c")
            username = record.get("username")
            user_id = record.get("user_id")
            profile_picture = record.get("profile_picture")
        elif isinstance(record, (list, tuple)):
            r = record[0].get("c") if isinstance(record[0], dict) else record[0]
            username = record[1] if len(record) > 1 else current_user.get("username")
            user_id = record[2] if len(record) > 2 else current_user["user_id"]
            profile_picture = None
        else:
            raise HTTPException(status_code=500, detail="Unexpected Neo4j reply structure")

        if not r:
            raise HTTPException(status_code=500, detail="Failed to create reply — missing node data")

        created_at = r.get("created_at")
        if hasattr(created_at, "to_native"):
            created_at = created_at.to_native()

        return ReplyResponse(
            reply_id=r["id"],
            content=r["content"],
            created_at=created_at,
            username=username or current_user.get("username", "Unknown"),
            user_id=user_id or current_user["user_id"],
            image_url=r.get("image_url"),
            profile_picture=profile_picture
        )

    except Exception as e:
        print(f"⚠️ Error in create_reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get comments with nested replies
def get_comments(post_id: str):
    db = get_db()
    query = """
    MATCH (u:User)-[:COMMENTED]->(c:Comment)-[:ON]->(p:Post {id: $post_id})
    OPTIONAL MATCH (c)<-[:REPLIED_TO]-(r:Comment)<-[:COMMENTED]-(ru:User)
    RETURN c, u.username AS username, u.user_id AS user_id, u.profile_picture AS profile_picture,
           collect({reply: r, reply_user: ru.username, reply_user_id: ru.user_id, reply_profile: ru.profile_picture}) AS replies
    ORDER BY c.created_at ASC
    """
    try:
        result = db.execute_query(query, {"post_id": post_id}, database_="neo4j")

        # 🧩 Handle Neo4j EagerResult directly
        records = []
        if hasattr(result, "records"):
            records = result.records
        elif isinstance(result, list):
            records = result
        else:
            raise HTTPException(status_code=500, detail="Unexpected response format from Neo4j")

        comments = []
        for record in records:
            # Access record fields by key (not .get)
            c = record["c"]
            if not c:
                continue

            created_at = neo4j_datetime_to_python(c["created_at"])
            replies_data = record["replies"] or []

            replies = []
            for reply_data in replies_data:
                r = reply_data.get("reply")
                if r:
                    replies.append(ReplyResponse(
                        reply_id=r.get("id"),
                        content=r.get("content"),
                        created_at=neo4j_datetime_to_python(r.get("created_at")),
                        username=reply_data.get("reply_user"),
                        user_id=reply_data.get("reply_user_id"),
                        image_url=r.get("image_url"),
                        profile_picture=reply_data.get("reply_profile")
                    ))

            comments.append(CommentResponse(
                comment_id=c["id"],
                post_id=post_id,
                content=c["content"],
                created_at=created_at,
                username=record["username"],
                user_id=record["user_id"],
                image_url=c.get("image_url"),
                profile_picture=record.get("profile_picture"),
                replies=replies
            ))

        return {"comments": comments}

    except Exception as e:
        print(f"⚠️ Error in get_comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Update and delete remain mostly the same, just ensure datetime is handled if needed
# ✅ Delete a comment or reply
def delete_comment(comment_id: str, current_user: dict):
    db = get_db()

    try:
        # Fetch author
        check_query = """
        MATCH (c:Comment {id: $comment_id})
        OPTIONAL MATCH (c)<-[:COMMENTED]-(u:User)
        RETURN c, u.user_id AS author_id
        """
        result = db.execute_query(check_query, {"comment_id": comment_id}, database_="neo4j")

        records = result.get("records", []) if isinstance(result, dict) else result
        if not records:
            raise HTTPException(status_code=404, detail="Comment not found")

        record = records[0]
        c = record.get("c") if isinstance(record, dict) else record[0]
        author_id = record.get("author_id") if isinstance(record, dict) else None

        if not c:
            raise HTTPException(status_code=404, detail="Comment node missing")

        if author_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

        # Delete
        delete_query = """
        MATCH (c:Comment {id: $comment_id})
        DETACH DELETE c
        RETURN COUNT(c) AS deleted
        """
        del_result = db.execute_query(delete_query, {"comment_id": comment_id}, database_="neo4j")
        deleted_records = del_result.get("records", []) if isinstance(del_result, dict) else del_result
        deleted = deleted_records[0].get("deleted") if deleted_records and isinstance(deleted_records[0], dict) else 1

        if deleted == 0:
            raise HTTPException(status_code=500, detail="Failed to delete comment")

        return {"message": "Comment deleted successfully", "comment_id": comment_id}

    except Exception as e:
        print(f"⚠️ Error in delete_comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
