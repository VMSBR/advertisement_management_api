from fastapi import Depends, HTTPException
from datetime import datetime, timedelta, timezone
import os
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db import users_collection
from utils import replace_mongo_id
from bson.objectid import ObjectId

SECRET = os.getenv("JWT_SECRET_KEY", "supersecret")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 5
bearer = HTTPBearer()

def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)

def decode_token(token: str):
    try:
        data = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        return data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    payload = decode_token(credentials.credentials)
    user = users_collection.find_one({"_id": ObjectId(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return replace_mongo_id(user)

def vendor_only(user: dict = Depends(get_current_user)):
    if user["role"] != "vendor":
        raise HTTPException(status_code=403, detail="Vendor access required")
    return user
