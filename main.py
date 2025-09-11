from fastapi import FastAPI, Form, File, UploadFile, HTTPException, status
from db import adverts_collection
from pydantic import BaseModel
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

# configure cloudinary
cloudinary.config(
    cloud_name = os.getenv("CLOUD_NAME"),
    api_key = os.getenv("API_KEY"),
    api_secret = os.getenv("API_SECRET"),
)
    

tags_metadata = [
    {
        "name": "Home",
        "description": "Welcome to Our Advertisement Management API",
    },
    {
        "name": "Adverts",
        "descriptions": "Adverts of Agricultural Produce",
    },
]

class AdvertModel(BaseModel):
    title: str
    description: str
    price: float
    quantity: int
    flyer: UploadFile
    
app = FastAPI(openapi_tags=tags_metadata)


# Homepage
@app.get("/", tags=["Home"])
def get_home():
    return {"message": "Oh hello! Akwaaba! Welcome to AGROKASA!"}


# Endpoints for Adding adverts
@app.post("/adverts", tags=["Adverts"])
def post_adverts(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
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
        }
    )
    # Return response
    return {"message": "Advert added successfully!"}


# Get advert endpoint
@app.get("/adverts", tags=["Adverts"])
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
@app.get("/adverts/{advert_id}", tags=["Adverts"])
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


@app.put("/adverts/{advert_id}", tags=["Adverts"])
def replace_advert(
    advert_id,
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
):
    # Check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
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
        },
    )
    if not result.modified_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advert with ID {advert_id} not found to update.")
    # Return response
    return {"message": "Hooray! Advert replaced successfully"}


@app.delete("/adverts/{advert_id}", tags=["Adverts"])
def delete_advert(advert_id):
    # Check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Delete advert from database
    delete_result = adverts_collection.delete_one(filter={"_id": ObjectId(advert_id)})
    if not delete_result.deleted_count:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Sorry, no event found to delete!"
        )
    # Return reponse
    return {"message": "Advert deleted successfully!"}
