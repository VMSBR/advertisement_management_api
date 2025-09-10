from fastapi import FastAPI, Form, File, UploadFile, HTTPException, status
from db import adverts_collection
from db import vendors_collection
from pydantic import BaseModel
from bson.objectid import ObjectId
from utils import replace_mongo_id
from typing import Annotated
import cloudinary
import cloudinary.uploader

# Configure cloudinary
cloudinary.config(
    cloud_name="dh642puxk",
    api_key="413358591893165",
    api_secret="-irAwuqqrhNgOXz-A_wKUoKz9pU",
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
    {"name": "Vendor Signup/Login", "description": "You may signup/login now"},
]

app = FastAPI(openapi_tags=tags_metadata)

# A list to store my registered vendors
vendors = []


# Pydantic models for request
class VendorSignup(BaseModel):
    username: str
    email: str
    password: str


class VendorLogin(BaseModel):
    username_or_email: str
    password: str


# Homepage
@app.get("/", tags=["Home"])
def get_home():
    return {"message": "Oh hello! Akwaaba! Welcome to AGROKASA!"}


# Endpoints for Adding adverts
@app.post("/adverts", tags=["Adverts"])
def post_adverts(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
):
    #Check if the vendor exists and credentials are correct ---
    vendor = vendors_collection.find_one({"username": username, "password": password})
    if not vendor:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid credentials. You must be a registered vendor to post an advert.",
        )
    try:
        # Upload flyer to cloudinary to get a url
        upload_result = cloudinary.uploader.upload(flyer.file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cloudinary upload failed: {e}",
        )
    # Insert event into database
    adverts_collection.insert_one(
        {
            "title": title,
            "description": description,
            "price": price,
            "quantity": quantity,
            "flyer": upload_result["secure_url"],
            "vendor_id": vendor["_id"],
        }
    )
    # Return response
    return {"message": "Advert added successfully!"}



class AdvertResponse(BaseModel):
    id: str
    title: str
    description: str
    quantity: int
    flyer: str
    price: float
    vendor_id: str


# Get advert endpoint
@app.get("/adverts", tags=["Adverts"], response_model= list[AdvertResponse])
def get_adverts(title="", description="", limit=10, skip=0):
    # Get all events from database
    adverts_cursor = adverts_collection.find(
        filter={
            "$or": [
                {"title": {"$regex": title, "$options": "i"}},
                {"description": {"$regex": description, "$options": "i"}},
            ]
        },
        limit=int(limit),
        skip=int(skip),
    )
    adverts_list = list(adverts_cursor)
    processed_adverts= []
    for advert in adverts_list:
        advert["vendor_id"]= str(advert["vendor_id"])
        processed_adverts.append(replace_mongo_id(advert))
    # Return response
    return processed_adverts

# Vendors signup endpoint
@app.post("/register", tags=["Vendor Signup/Login"])
def register_vendor(vendor: VendorSignup):
      # Check if vendor already exists
    existing_vendor = vendors_collection.find_one(
        {"$or": [{"username": vendor.username}, {"email": vendor.email}]}
    )
    if existing_vendor:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Uh-oh! A vendor with these details already exists!"
        )
    # Insert user into database
    vendors_collection.insert_one(vendor.model_dump())
    return {"message": "Hooray! Vendor successfully registered!"}


@app.post("/login", tags=["Vendor Signup/Login"])
def login_vendor(user_name: str, user_password: str):
    # search through users to find a match
    vendor = vendors_collection.find_one(
        {
            "$or": [{"username": user_name}, {"email": user_name}],
            "password": user_password,
        }
    )
    # If a match is found
    if vendor:
        return {"message": "Login successful", "vendor": replace_mongo_id(vendor)}
    # If no match is found
    if not vendor:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sorry, your credentials are invalid")


# Get advert by advert details
@app.get("/adverts/{advert_id}", tags=["Adverts"], response_model=AdvertResponse)
def get_advert_by_id(advert_id:str):
    # check if event id is valid
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # Get event from database by id_
    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found!")
    advert["id"]=str(advert["_id"])
    advert["vendor_id"] = str(advert["vendor_id"])
    # Return response
    return replace_mongo_id(advert)


@app.put("/adverts/{advert_id}", tags= ["Adverts"])
def replace_advert(
    advert_id: str,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    quantity: Annotated[int, Form()],
    flyer: Annotated[UploadFile, File()],
):
    # Check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )

    # Upload flyer to cloudinary
    try:
        upload_result = cloudinary.uploader.upload(flyer.file)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Cloudinary upload failed: {e}")

    # Verify vendor
    adverts_collection.find_one(advert_id)
    # Replace advert in database
    result = adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id)},
        replacement={
            "title": title,
            "description": description,
            "price": price,
            "quantity": quantity,
            "flyer": upload_result["secure_url"],
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found")

    # Return response
    return {"message": "Hooray! Advert replaced successfully"}

@app.delete("/adverts/{advert_id}", tags= ["Adverts"])
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
