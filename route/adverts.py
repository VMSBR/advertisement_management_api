from fastapi import Form, File, UploadFile, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles

# Create adverts router
adverts_router = APIRouter()

# Endpoints for Adding adverts
@adverts_router.post("/adverts", tags=["Adverts"], dependencies=[Depends(has_roles(["vendor", "admin"]))])
def post_adverts(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
    user_id: Annotated[str, Depends(is_authenticated)]
    
):
    advert_count = adverts_collection.count_documents(
        filter ={
            "$and": [
                {"title": title},
                {"owner": user_id}
            ]
        }
    )
    if advert_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Advert with {title} and {ObjectId(user_id)} already exist!"
        )
    upload_result = cloudinary.uploader.upload(flyer.file)
    # Insert advert into database
    adverts_collection.insert_one(
        {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "quantity": quantity,
            "flyer": upload_result["secure_url"],
            "owner": user_id,
        }
    )
    # Return response
    return {"message": "Advert added successfully!"}


# Get advert endpoint
@adverts_router.get("/adverts", tags=["Adverts"])
def get_adverts(title="", description="", limit=10, skip=0):
    # Get all adverts from database
    adverts = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": title, "$options": "i"}},
                {"description": {"$regex": description, "$options": "i"}},
            ]
        },
        limit=int(limit),
        skip=int(skip),
    ).to_list()
    # Return response
    return {"data": list(map(replace_mongo_id, adverts))}

# Get advert by advert details
@adverts_router.get("/adverts/{advert_id}", tags=["Adverts"])
def get_advert_by_id(advert_id):
    # check if advert id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get advert from database by id_
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    # Return response
    return {"data": replace_mongo_id(advert)}


@adverts_router.put("/adverts/{advert_id}", tags=["Adverts"], dependencies=[Depends(has_roles(["vendor", "admin"]))])
def replace_advert(
    advert_id: str,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
    user_id: Annotated[str, Depends(is_authenticated)]
):
    if not adverts_collection.find_one({"_id": ObjectId(advert_id)}):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No advert found to replace!"
        )
    # check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # upload flyer to cloudinary to get a url
    upload_result = cloudinary.uploader.upload(flyer.file)
    # replace advert in database
    adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id)},
        replacement={
        "title": title,
        "description": description,
        "price": price,
        "category": category,
        "quantity": quantity,
        "flyer": upload_result["secure_url"],
        "owner": user_id,
    },
    )
    # Return response
    return {"message": "Hooray! Advert replaced successfully"}

@adverts_router.delete("/adverts/{advert_id}", tags=["Adverts"], dependencies=[Depends(has_roles(["vendor", "admin"]))])
def delete_advert(advert_id, user_id: Annotated[str, Depends(is_authenticated)]):
    # Check if advert_id is a valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received")
    # Delete advert from database
    delete_result = adverts_collection.delete_one(
        filter={"_id": ObjectId(advert_id)})
    if not delete_result.deleted_count:
        raise HTTPException (status.HTTP_404_NOT_FOUND, "No advert found to delete!")
    # Return response
    return {"message": "Advert deleted succesfully!", "user_id": user_id}

# In adverts.py

@adverts_router.get("/adverts/user/me", tags=["Vendor Dashboard"], dependencies=[Depends(has_roles(["vendor", "admin"]))])
def get_my_adverts(current_user_id: Annotated[str, Depends(is_authenticated)]):
    """
    Retrieves all adverts posted by the currently authenticated vendor.
    'is_authenticated' provides the user ID string directly.
    """
    # Use the user ID string directly in the database query.
    adverts_cursor = adverts_collection.find(
        filter={"owner": current_user_id}
    )

    adverts_list = list(adverts_cursor)

    # Return response, ensuring MongoDB's _id is handled if necessary
    return {"data": list(map(replace_mongo_id, adverts_list))}
