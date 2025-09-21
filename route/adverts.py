from fastapi import Form, File, UploadFile, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader
from dependencies.authorize import vendor_only

# Create adverts router
adverts_router = APIRouter()

# Endpoints for Adding adverts
@adverts_router.post("/adverts", tags=["Adverts"])
def post_adverts(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
    user: dict = Depends(vendor_only)
    
):
    upload_result = cloudinary.uploader.upload(flyer.file)
    # Insert event into database
    adverts_collection.insert_one(
        {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "quantity": quantity,
            "flyer": upload_result["secure_url"],
            "vendor_id": user["id"],
        }
    )
    # Return response
    return {"message": "Advert added successfully!"}


# Get advert endpoint
@adverts_router.get("/adverts", tags=["Adverts"])
def get_adverts(title="", description="", limit=10, skip=0):
    # Get all events from database
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
    # check if event id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get event from database by id_
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    # Return response
    return {"data": replace_mongo_id(advert)}


@adverts_router.put("/adverts/{advert_id}", tags=["Adverts"])
def replace_advert(
    advert_id: str,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
    user: dict = Depends(vendor_only)
):
    # Check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Check if the advert exists and belongs to the user
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert or advert["vendor_id"] != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to update this advert")

    # Upload flyer to cloudinary
    upload_result = cloudinary.uploader.upload(flyer.file)
    # Replace advert in database
    result = adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id)},
        replacement={
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "quantity": quantity,
            "flyer": upload_result["secure_url"],
            "vendor_id": user["id"],
        },
    )
    if not result.modified_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advert with ID {advert_id} not found to update.")
    # Return response
    return {"message": "Hooray! Advert replaced successfully"}


@adverts_router.delete("/adverts/{advert_id}", tags=["Adverts"])
def delete_advert(advert_id: str, user: dict = Depends(vendor_only)):
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!")

    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert or advert["vendor_id"] != user["id"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this advert")

    delete_result = adverts_collection.delete_one({"_id": ObjectId(advert_id)})
    if not delete_result.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sorry, no advert found to delete!")

    return {"message": "Advert deleted successfully!"}