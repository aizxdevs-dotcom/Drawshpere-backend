from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.controllers import user_controller
from app.auth import get_current_user
from app.models.user_model import User, UpdateUser, LoginRequest

router = APIRouter(tags=["Users"])


@router.post("/register")
def register(user: User):
    """Register a new user"""
    return user_controller.register_user(user)

@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Return full info about the currently logged-in user.
    """
    from app.db import get_db
    db = get_db()

    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user token")

    with db.session() as session:
        query = """
        MATCH (u:User {user_id: $user_id})
        RETURN u
        """
        result = session.run(query, user_id=user_id)
        record = result.single()

        if not record:
            raise HTTPException(status_code=404, detail="User not found")

        user = record["u"]

        return {
            "user_id": user["user_id"],
            "username": user.get("username"),
            "name": user.get("name"),
            "email": user.get("email")
        }

@router.post("/login")
def login(login_request: LoginRequest):
    """Login and get JWT token"""
    return user_controller.authenticate_user(login_request)


@router.get("/")
def list_users():
    return user_controller.get_users()


@router.get("/{email}")
def get_user(email: str):
    return user_controller.get_user_by_email(email)


@router.put("/{email}")
def update_user(email: str, data: UpdateUser):
    return user_controller.update_user(email, data)


@router.delete("/{email}")
def remove_user(email: str):
    return user_controller.delete_user(email)


@router.post("/upload-profile-picture")
async def upload_profile_picture(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload or update profile picture for current user"""
    return await user_controller.upload_profile_picture(image, current_user)
