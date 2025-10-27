from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# ===========================
# 🔐 JWT CONFIGURATION
# ===========================
SECRET_KEY = os.getenv("SECRET_KEY", "123236")  # read from env with fallback
ALGORITHM = "HS256"
# Set default token expiry to 7 days (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60  # 10080 minutes

# Initialize HTTP Bearer (instead of OAuth2)
security = HTTPBearer()


# ===========================
# ✅ CREATE ACCESS TOKEN
# ===========================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a signed JWT token with expiration time.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


# ===========================
# ✅ VERIFY CURRENT USER
# ===========================
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Decode JWT from HTTP Bearer token and return user info.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )

        return {"user_id": user_id, "username": username}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again.",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or corrupted token.",
        )
