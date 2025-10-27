from pydantic import BaseModel, EmailStr
from typing import Optional


class User(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str
    profile_picture: Optional[str] = None


class UpdateUser(BaseModel):
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    profile_picture: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

