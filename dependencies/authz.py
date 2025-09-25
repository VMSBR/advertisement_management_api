from dependencies.authn import authenticated_user
from fastapi import Depends, HTTPException, status
from typing import Annotated


permissions = [
    {
        "role":"admin",
        "permissions":["*"]
    },
    {
        "role":"vendor",
        "permissions":[
            "post_adverts",
            "get_adverts",
            "get_advert_by_id",
            "get_similar_adverts",
            "get_my_adverts"
            "replace_advert",
            "delete_advert",
        ]
    },
    {
        "role":"user",
        "permissions":[
            "get_adverts",
            "get_advert_by_id",
            "get_similar_adverts"
        ]
    }
]


def has_roles(roles):
    def check_roles(user: Annotated[any, Depends(authenticated_user)]):
        if user["role"] not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Access denied!"
            )

    return check_roles

def has_permission(permission):
    def check_permission(user: Annotated[any, Depends(authenticated_user)]):
        role = user.get("role")
        for entry in permissions:
            if entry["role"] == role:
                perms = entry.get("permissions", [])
                if "*" in perms or permission in perms:
                    return user
                break
            raise HTTPException(status. HTTP_403_FORBIDDEN,"Permission denied")
        return check_permission