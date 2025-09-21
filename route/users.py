from fastapi import APIRouter, Form, HTTPException, status
from typing import Annotated
from pydantic import EmailStr
from db import users_collection
import bcrypt
from dependencies.authorize import create_token


users_router = APIRouter()


@users_router.post("/users/register", tags=["Users"])
def register_user(
    username: Annotated[str, Form()],
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
    role: Annotated[str, Form()] = "user",  # role: user or vendor
):
    if role not in ["user", "vendor"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role must be 'user' or 'vendor'")

    if users_collection.count_documents({"email": email}) > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    users_collection.insert_one(
        {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
        }
    )
    return {"message": "User registered successfully!"}


@users_router.post("/users/login", tags=["Users"])
def login_user(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
):
    user_in_db = users_collection.find_one({"email": email})
    if not user_in_db:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User does not exist!")

    if not bcrypt.checkpw(password.encode("utf-8"), user_in_db["password"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = create_token(str(user_in_db["_id"]), user_in_db["role"])

    return {
        "message": "User logged in successfully!",
        "access_token": token,
    }
