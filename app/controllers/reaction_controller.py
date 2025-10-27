from fastapi import HTTPException
from app.db import get_db
from app.models.reaction import ReactionCreate, ReactionResponse
from app.controllers import notification_controller
from datetime import datetime
from app.auth import SECRET_KEY, ALGORITHM
from jose import jwt

def create_reaction(reaction: ReactionCreate, current_user: dict):
    db = get_db()
    
    # First get the post author to create notification
    post_query = """
    MATCH (p:Post {id: $post_id})<-[:CREATED]-(author:User)
    RETURN author.user_id AS author_id
    """
    post_result = db.execute_query(post_query, {"post_id": reaction.post_id}, database_="neo4j")
    post_records = post_result[0] if post_result and len(post_result) > 0 else []
    
    author_id = post_records[0].get("author_id") if post_records else None
    
    # Use MERGE to ensure a single REACTED relationship per user-post pair
    # If it exists, update the type; otherwise create it.
    query = """
    MATCH (u:User {user_id: $user_id}), (p:Post {id: $post_id})
    MERGE (u)-[r:REACTED]->(p)
    SET r.type = $type, r.created_at = datetime()
    RETURN r, u.user_id AS user_id, u.username AS username, p.id AS post_id
    """
    try:
        result = db.execute_query(
            query,
            {
                "user_id": current_user["user_id"],
                "post_id": reaction.post_id,
                "type": reaction.type,
            },
            database_="neo4j",
        )

        if not result or not result[0]:
            raise HTTPException(status_code=500, detail="Failed to create reaction")

        record = result[0][0]
        created_at = record["r"]["created_at"]
        if hasattr(created_at, "to_native"):
            created_at = created_at.to_native()
        
        # Create notification for post author (only if author exists and actor is not the author)
        if author_id and author_id != current_user.get("user_id"):
            notification_controller.create_notification(
                user_id=author_id,
                actor_id=current_user["user_id"],
                notification_type=reaction.type,  # "like", "love", "haha", "care"
                post_id=reaction.post_id
            )

        return ReactionResponse(
            reaction_id=f"{record['user_id']}_{record['post_id']}",
            post_id=record["post_id"],
            user_id=record["user_id"],
            username=record["username"],
            type=record["r"]["type"],
            created_at=created_at,
        )

    except Exception as e:
        print(f"⚠️ Error in create_reaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_all_reactions():
    """
    Fetch all reactions with related users (username) and posts.
    Handles both Neo4j Aura list and Record structures.
    """
    db = get_db()
    query = """
    MATCH (u:User)-[r:REACTED]->(p:Post)
    RETURN r AS reaction, u AS user, p AS post
    ORDER BY r.created_at DESC
    """

    try:
        result = db.execute_query(query, database_="neo4j")
        # Depending on driver version, `result` may be dict or list-like
        records = result.get("records", []) if isinstance(result, dict) else result

        def to_props(obj):
            """Convert a neo4j Node/Relationship or mapping to a plain dict of properties."""
            if obj is None:
                return {}
            # If already a dict-like
            if isinstance(obj, dict):
                return obj
            try:
                return dict(obj)
            except Exception:
                # Try .properties (some neo4j wrappers expose this)
                if hasattr(obj, "properties"):
                    try:
                        return dict(obj.properties)
                    except Exception:
                        return {}
                return {}

        reactions = []
        for record in records:
            # Accept dict-like records or sequence records
            if isinstance(record, dict):
                r_raw = record.get("reaction")
                u_raw = record.get("user")
                p_raw = record.get("post")
            else:
                # some drivers return neo4j.Record which behaves like a sequence
                try:
                    r_raw, u_raw, p_raw = record
                except Exception:
                    # skip invalid structures
                    continue

            reaction_props = to_props(r_raw)
            user_props = to_props(u_raw)
            post_props = to_props(p_raw)

            created_at = reaction_props.get("created_at")
            if hasattr(created_at, "to_native"):
                created_at = created_at.to_native()

            created_at_val = (
                created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
            ) if created_at is not None else None

            reactions.append({
                "reaction_id": f"{user_props.get('user_id')}_{post_props.get('id')}",
                "post_id": post_props.get("id"),
                "user_id": user_props.get("user_id"),
                "username": user_props.get("username"),
                "type": reaction_props.get("type"),
                "created_at": created_at_val,
            })

        return reactions

    except Exception as e:
        print(f"⚠️ Error in get_all_reactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def delete_reaction(post_id: str, current_user: dict):
    """
    Delete the REACTED relationship for the current user on the given post.
    """
    db = get_db()
    query = """
    MATCH (u:User {user_id: $user_id})-[r:REACTED]->(p:Post {id: $post_id})
    WITH u, p, r.type AS type
    DELETE r
    RETURN u.user_id AS user_id, p.id AS post_id, type AS type
    """

    try:
        result = db.execute_query(query, {"user_id": current_user["user_id"], "post_id": post_id}, database_="neo4j")
        # result may be list-like or dict depending on driver
        records = result[0] if isinstance(result, (list, tuple)) and len(result) > 0 else (result.get("records") if isinstance(result, dict) else result)

        # If deletion succeeded, return a small payload
        return {"success": True, "post_id": post_id}
    except Exception as e:
        print(f"⚠️ Error in delete_reaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_reactions_for_post(post_id: str, token: str | None = None):
    """
    Return aggregated reaction counts for a post and optionally the current user's reaction if a valid token is provided.
    Response shape: { counts: {like, love, haha, care, total}, user_reaction: str|null, reactions: [..] }
    """
    db = get_db()
    user_id = None
    if token:
        try:
            # token is expected to be the raw token string (without 'Bearer')
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except Exception:
            user_id = None

    # Aggregate counts per type
    counts_query = """
    MATCH (:User)-[r:REACTED]->(p:Post {id: $post_id})
    RETURN r.type AS type, count(r) AS cnt
    """

    # If token present, fetch user's reaction type directly
    user_query = """
    MATCH (u:User {user_id: $user_id})-[r:REACTED]->(p:Post {id: $post_id})
    RETURN r.type AS type
    """

    try:
        counts_result = db.execute_query(counts_query, {"post_id": post_id}, database_="neo4j")
        counts_records = counts_result.get("records", []) if isinstance(counts_result, dict) else counts_result

        counts = {"like": 0, "love": 0, "haha": 0, "care": 0, "total": 0}
        for rec in counts_records:
            # rec may be dict-like or tuple-like
            if isinstance(rec, dict):
                t = rec.get("type")
                c = rec.get("cnt")
            else:
                try:
                    t, c = rec
                except Exception:
                    continue
            if t and counts.get(t) is not None:
                counts[t] = int(c)
                counts["total"] += int(c)

        user_reaction = None
        if user_id:
            try:
                user_result = db.execute_query(user_query, {"post_id": post_id, "user_id": user_id}, database_="neo4j")
                user_records = user_result.get("records", []) if isinstance(user_result, dict) else user_result
                if user_records:
                    # record may be dict-like or tuple-like
                    rec = user_records[0]
                    if isinstance(rec, dict):
                        user_reaction = rec.get("type")
                    else:
                        try:
                            user_reaction = rec[0]
                        except Exception:
                            user_reaction = None
            except Exception:
                user_reaction = None

        return {"counts": counts, "user_reaction": user_reaction}

    except Exception as e:
        print(f"⚠️ Error in get_reactions_for_post: {e}")
        raise HTTPException(status_code=500, detail=str(e))
