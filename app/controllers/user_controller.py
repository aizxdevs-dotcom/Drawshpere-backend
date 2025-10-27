import uuid
from datetime import timedelta
from fastapi import HTTPException, UploadFile
from app.db import get_db, hash_password, verify_password
from app.models.user_model import User, UpdateUser, LoginRequest
from app.auth import create_access_token
from app.cloudinary_util import upload_image


def register_user(user: User):
    db = get_db()
    hashed_password = hash_password(user.password)

    with db.session() as session:
        # Check if user exists
        query = """
        MATCH (u:User)
        WHERE u.email = $email OR u.username = $username
        RETURN u
        """
        result = session.run(query, email=user.email, username=user.username)
        if result.single():
            raise HTTPException(status_code=400, detail="Username or email already exists")

        user_id = str(uuid.uuid4())

        query = """
        CREATE (u:User {
            user_id: $user_id,
            username: $username,
            name: $name,
            email: $email,
            password: $password
        })
        RETURN u
        """
        session.run(
            query,
            user_id=user_id,
            username=user.username,
            name=user.name,
            email=user.email,
            password=hashed_password,
        )

        return {"message": "User registered successfully", "user_id": user_id}


def authenticate_user(login_request: LoginRequest):
    db = get_db()
    with db.session() as session:
        try:
            print("🔍 Checking email:", login_request.email)
            query = "MATCH (u:User {email: $email}) RETURN u"
            result = session.run(query, email=login_request.email)
            record = result.single()

            if not record:
                raise HTTPException(status_code=404, detail="User not found")

            user = record["u"]
            print("✅ Found user:", user)

            # Verify password
            if not verify_password(login_request.password, user["password"]):
                print("❌ Wrong password")
                raise HTTPException(status_code=401, detail="Invalid credentials")

            if "user_id" not in user:
                print("⚠️ user_id missing from DB node:", user)
                raise HTTPException(status_code=500, detail="Missing user_id in database")

            # Generate JWT (include username to avoid extra DB lookups downstream)
            access_token_expires = timedelta(minutes=30)
            token = create_access_token(
                {
                    "sub": user["user_id"],
                    "username": user.get("username")
                },
                expires_delta=access_token_expires
            )

            print("🎟 Token generated successfully")
            return {
                "message": "Login successful",
                "access_token": token,
                "token_type": "bearer"
            }

        except Exception as e:
            print("🔥 LOGIN ERROR:", e)
            raise HTTPException(status_code=500, detail=str(e))



def get_users():
    
    db = get_db()
    with db.session() as session:
        query = "MATCH (u:User) RETURN u"
        results = session.run(query)
        users = [record["u"] for record in results]
        return {"users": users}


def get_user_by_email(email: str):
    db = get_db()
    with db.session() as session:
        query = "MATCH (u:User {email: $email}) RETURN u"
        result = session.run(query, email=email)
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user": record["u"]}


def update_user(email: str, data: UpdateUser):
    db = get_db()
    with db.session() as session:
        updates = {k: v for k, v in data.dict().items() if v is not None}
        query = """
        MATCH (u:User {email: $email})
        SET u += $updates
        RETURN u
        """
        result = session.run(query, email=email, updates=updates)
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User updated", "user": record["u"]}


def delete_user(email: str):
    db = get_db()
    with db.session() as session:
        query = "MATCH (u:User {email: $email}) DETACH DELETE u RETURN COUNT(u) AS deleted"
        result = session.run(query, email=email)
        count = result.single()["deleted"]
        if count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User deleted"}


async def upload_profile_picture(image: UploadFile, current_user: dict):
    """Upload or update user profile picture"""
    db = get_db()
    
    # Upload image to Cloudinary
    result = await upload_image(image, folder="drawsphere/profiles")
    image_url = result["url"]
    
    with db.session() as session:
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.profile_picture = $profile_picture
        RETURN u
        """
        result = session.run(query, user_id=current_user["user_id"], profile_picture=image_url)
        record = result.single()
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "message": "Profile picture updated successfully",
            "profile_picture": image_url
        }
