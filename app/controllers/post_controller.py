from fastapi import HTTPException, status, UploadFile
from datetime import datetime as _py_datetime
from app.db import get_db
from app.models.post import PostCreate, PostUpdate
from app.cloudinary_util import upload_image, delete_image
from typing import Optional


# ========================================
# ✅ CREATE POST (Authenticated)
# ========================================
async def create_post(content: str, image: Optional[UploadFile], current_user: dict):
    db = get_db()
    
    # Upload image to Cloudinary if provided
    image_url = None
    if image:
        result = await upload_image(image, folder="drawsphere/posts")
        image_url = result["url"]

    query = """
    MATCH (u:User {user_id: $author_id})
    CREATE (u)-[:CREATED]->(p:Post {
        id: randomUUID(),
        content: $content,
        image_url: $image_url,
        created_at: datetime(),
        author_id: $author_id
    })
    RETURN p, u.username AS username, u.profile_picture AS profile_picture
    """

    result = db.execute_query(
        query,
        {
            "content": content,
            "image_url": image_url,
            "author_id": current_user["user_id"]
        },
        database_="neo4j"
    )

    # ✅ Neo4j returns (records, summary, keys)
    records = result[0]
    record = records[0] if records else None

    if not record:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post"
        )

    post_node = record["p"]
    post_data = dict(post_node)
    # normalize Neo4j datetime objects to ISO strings for the frontend
    try:
        ca = post_node.get("created_at")
        if ca is not None:
            # handle Neo4j datetime wrappers
            if hasattr(ca, "to_native"):
                native = ca.to_native()
                if isinstance(native, _py_datetime):
                    post_data["created_at"] = native.isoformat()
                else:
                    post_data["created_at"] = str(native)
            elif isinstance(ca, _py_datetime):
                post_data["created_at"] = ca.isoformat()
            else:
                post_data["created_at"] = str(ca)
    except Exception:
        # fallback: leave as-is
        pass
    post_data["id"] = str(post_node.get("id"))
    post_data["author_id"] = current_user["user_id"]
    post_data["username"] = record.get("username")
    post_data["profile_picture"] = record.get("profile_picture")

    return {
        "message": "Post created successfully",
        "post": post_data
    }

# ========================================
# ✅ GET ALL POSTS (Public)
# ========================================
def get_all_posts():
    db = get_db()

    query = """
    MATCH (u:User)-[:CREATED]->(p:Post)
    RETURN p, u.user_id AS user_id, u.username AS username, u.profile_picture AS profile_picture
    ORDER BY p.created_at DESC
    """

    try:
        result = db.execute_query(query, database_="neo4j")
        records = result[0] if result and len(result) > 0 else []

        posts = []
        for record in records:
            post_node = record["p"]
            post_data = dict(post_node)
            # normalize created_at to a string (ISO) so frontend's Date parsing works
            try:
                ca = post_node.get("created_at")
                if ca is not None:
                    if hasattr(ca, "to_native"):
                        native = ca.to_native()
                        if isinstance(native, _py_datetime):
                            post_data["created_at"] = native.isoformat()
                        else:
                            post_data["created_at"] = str(native)
                    elif isinstance(ca, _py_datetime):
                        post_data["created_at"] = ca.isoformat()
                    else:
                        post_data["created_at"] = str(ca)
            except Exception:
                pass
            post_data["author_id"] = record.get("user_id")
            post_data["username"] = record.get("username")
            post_data["profile_picture"] = record.get("profile_picture")
            posts.append(post_data)

        return {"total": len(posts), "posts": posts}

    except Exception as e:
        print(f"⚠️ Error in get_all_posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# ✅ GET POST BY ID (Authenticated)
# ========================================
def get_post_by_id(post_id: str):
    db = get_db()
    query = """
    MATCH (u:User)-[:CREATED]->(p:Post {id: $id})
    RETURN p, u.user_id AS user_id, u.username AS username
    """
    result = db.execute_query(query, {"id": post_id}, database_="neo4j")
    records = result.get("records", []) if isinstance(result, dict) else result

    if not records:
        raise HTTPException(status_code=404, detail="Post not found")

    record = records[0]
    post_node = record["p"]

    post_data = dict(post_node)
    try:
        ca = post_node.get("created_at")
        if ca is not None:
            if hasattr(ca, "to_native"):
                native = ca.to_native()
                if isinstance(native, _py_datetime):
                    post_data["created_at"] = native.isoformat()
                else:
                    post_data["created_at"] = str(native)
            elif isinstance(ca, _py_datetime):
                post_data["created_at"] = ca.isoformat()
            else:
                post_data["created_at"] = str(ca)
    except Exception:
        pass
    post_data["author_id"] = record["user_id"]
    post_data["username"] = record["username"]

    return {"post": post_data}


# ========================================
# ✅ UPDATE POST (Authenticated + Ownership Check)
# ========================================
async def update_post(post_id: str, content: Optional[str], image: Optional[UploadFile], current_user: dict):
    db = get_db()
    user_id = current_user["user_id"]

    # Check ownership
    check_query = """
    MATCH (u:User {user_id: $user_id})-[:CREATED]->(p:Post {id: $id})
    RETURN p
    """
    check = db.execute_query(check_query, {"user_id": user_id, "id": post_id}, database_="neo4j")
    check_records = check.get("records", []) if isinstance(check, dict) else check
    if not check_records:
        raise HTTPException(status_code=403, detail="You are not allowed to update this post")

    # Upload new image if provided
    image_url = None
    if image:
        result = await upload_image(image, folder="drawsphere/posts")
        image_url = result["url"]

    # Build updates
    updates = {}
    if content is not None:
        updates["content"] = content
    if image_url is not None:
        updates["image_url"] = image_url
        
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Perform update
    update_query = """
    MATCH (p:Post {id: $id})
    SET p += $updates
    RETURN p
    """
    result = db.execute_query(update_query, {"id": post_id, "updates": updates}, database_="neo4j")
    records = result.get("records", []) if isinstance(result, dict) else result

    if not records:
        raise HTTPException(status_code=404, detail="Post not found")

    post_data = dict(records[0]["p"])
    # normalize created_at if present
    try:
        ca = records[0]["p"].get("created_at")
        if ca is not None:
            if hasattr(ca, "to_native"):
                native = ca.to_native()
                if isinstance(native, _py_datetime):
                    post_data["created_at"] = native.isoformat()
                else:
                    post_data["created_at"] = str(native)
            elif isinstance(ca, _py_datetime):
                post_data["created_at"] = ca.isoformat()
            else:
                post_data["created_at"] = str(ca)
    except Exception:
        pass
    return {"message": "Post updated successfully", "post": post_data}


# ========================================
# ✅ DELETE POST (Authenticated + Ownership Check)
# ========================================
def delete_post(post_id: str, current_user: dict):
    db = get_db()
    user_id = current_user["user_id"]

    # Check ownership
    check_query = """
    MATCH (u:User {user_id: $user_id})-[:CREATED]->(p:Post {id: $id})
    RETURN p
    """
    check = db.execute_query(check_query, {"user_id": user_id, "id": post_id}, database_="neo4j")
    check_records = check.get("records", []) if isinstance(check, dict) else check
    if not check_records:
        raise HTTPException(status_code=403, detail="You are not allowed to delete this post")

    # Delete post
    delete_query = """
    MATCH (p:Post {id: $id})
    DETACH DELETE p
    RETURN $id AS id
    """
    result = db.execute_query(delete_query, {"id": post_id}, database_="neo4j")
    records = result.get("records", []) if isinstance(result, dict) else result

    if not records:
        raise HTTPException(status_code=404, detail="Post not found")

    return {"message": "Post deleted successfully", "post_id": post_id}
