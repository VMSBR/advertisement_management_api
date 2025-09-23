from enum import Enum
from fastapi import APIRouter, Form, HTTPException, status
from typing import Annotated
from pydantic import EmailStr
from db import users_collection
import bcrypt
import jwt
import os
from datetime import datetime, timezone, timedelta

class UserRole(str, Enum):
    ADMIN = "Admin"
    HOST = "Vendor"
    GUEST = "User"

# Create users router
users_router = APIRouter()


# Define user endpoints
@users_router.post("/users/register", tags=["Users"])
def register_user( 
    username:Annotated[str,Form()],
    email:Annotated[EmailStr,Form()],
    password:Annotated[str,Form(min_length=8)],
    role: Annotated[UserRole, Form()] = UserRole.GUEST,
):
    # Ensure user does not exist
    user_count = users_collection.count_documents(filter={"email": email})
    if user_count > 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already exists")
    # Hash user password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    # Save user into database
    users_collection.insert_one(
        {"username": username,
        "email": email,
        "password": hashed_password,
        "role": role,}

    )
    # Return response
    return {"message": "User registered successfully!"}

@users_router.post("/users/login", tags=["Users"])
def login_user(
    email: Annotated[EmailStr, Form()],
    password: Annotated[str, Form(min_length=8)],
):
    #  find user in the database
    user_in_db = users_collection.find_one(filter={"email": email})
    # Check if the user exists and if the password is correct
    if not user_in_db:
        # User not found
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,"User does not exist!",
        )
    # Retrieve the hashed password from the database
    hashed_password_in_db = user_in_db["password"]
    
    # Verify the plain-text password against the stored hash
    correct_password = bcrypt.checkpw(
        password.encode("utf-8"), 
        hashed_password_in_db
    )
    if not correct_password:
        # Password does not match
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,"Incorrect email or password"
        )
    # Generate for them an access token
    encoded_jwt = jwt.encode({
        "id": str(user_in_db["_id"]),
        "exp": datetime.now(tz=timezone.utc)+ timedelta(minutes=25)},
        os.getenv("JWT_SECRET_KEY"), "HS256")
    # Return a success response 
    return {
        "message": "User logged in successfully!",
        "access_token": encoded_jwt
        }