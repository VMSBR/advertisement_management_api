from fastapi import Form, File, HTTPException, status, APIRouter, Depends
from db import adverts_collection
from bson.objectid import ObjectId
from utils import replace_mongo_id, genai_client
from typing import Annotated
import cloudinary
import cloudinary.uploader
from dependencies.authn import is_authenticated
from dependencies.authz import has_roles
from dotenv import load_dotenv
from google.genai import types


load_dotenv()

# Create adverts router
adverts_router = APIRouter()

# Endpoints for Adding adverts
@adverts_router.post(
    "/adverts",
    tags=["Vendor Dashboard"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def post_adverts(
    title: Annotated[str, Form()],
    description: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    flyer: Annotated[bytes, File()]=None,
):
    if not flyer:
        response=genai_client.models.generate_images(
            model = "imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        flyer =response.generated_images[0].image.image_bytes

    advert_count = adverts_collection.count_documents(
        filter={"$and": [{"title": title}, {"owner": user_id}]}
    )
    if advert_count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Advert with {title} and {ObjectId(user_id)} already exist!",
        )

    upload_result = cloudinary.uploader.upload(flyer)
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
@adverts_router.get("/adverts", tags=["User Dashboard"])
def get_adverts(
    search: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    limit: int = 10,
    skip: int = 0,
):
    # Query
    query_filter = {}

    # Keyword search on title and description
    if search:
        query_filter["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    # Filter by category
    if category:
        query_filter["category"] = {"$regex": f"^{category}$", "$options": "i"}

    # Filter by price range
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        query_filter["price"] = price_filter

    # Get all events from the database using the constructed filter
    adverts = list(
        adverts_collection.find(
            filter=query_filter,
            limit=int(limit),
            skip=int(skip),
        )
    )
    return {"data": list(map(replace_mongo_id, adverts))}


# Get advert by advert details
@adverts_router.get("/adverts/{advert_id}", tags=["User Dashboard"])
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


@adverts_router.get("/advert/{advert_id}/similar", tags=["User Dashboard"])
def get_similar_adverts(advert_id, limit=10, skip=0):
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )

    advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
    if not advert:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advert not found!")

    title = advert.get("title", "")
    category = advert.get("category", "")

    query_filter = {
        "$and": [
            {"_id": {"$ne": ObjectId(advert_id)}},
            {
                "$or": [
                    {"title": {"$regex": title, "$options": "i"}},
                    {"category": {"$regex": f"^{category}$", "$options": "i"}},
                ]
            },
        ]
    }

    similar_adverts = list(
        adverts_collection.find(
            filter=query_filter,
            limit=int(limit),
            skip=int(skip),
        )
    )

    return {"data": list(map(replace_mongo_id, similar_adverts))}

@adverts_router.put(
    "/adverts/{advert_id}",
    tags=["Vendor Dashboard"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def replace_advert(
    advert_id: str,
    description: Annotated[str, Form()],
    title: Annotated[str, Form()],
    price: Annotated[float, Form()],
    category: Annotated[str, Form()],
    quantity: Annotated[int, Form()],
    user_id: Annotated[str, Depends(is_authenticated)],
    flyer: Annotated[bytes, File()]=None,
):
    if not flyer:
        response=genai_client.models.generate_images(
            model = "imagen-4.0-generate-001",
            prompt=title,
            config=types.GenerateImagesConfig(number_of_images=1),
        )
        flyer =response.generated_images[0].image.image_bytes

    if not adverts_collection.find_one({"_id": ObjectId(advert_id)}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No advert found to replace!")
    # check if advert_id is valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received!"
        )
    # upload flyer to cloudinary to get a url
    upload_result = cloudinary.uploader.upload(flyer)
    # replace advert in database
    replace_result = adverts_collection.replace_one(
        filter={"_id": ObjectId(advert_id), "owner": user_id},
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
    if not replace_result.modified_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No advert found to replace!")
    # Return response
    return {"message": "Hooray! Advert replaced successfully"}


@adverts_router.delete(
    "/adverts/{advert_id}",
    tags=["Vendor Dashboard"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def delete_advert(advert_id, user_id: Annotated[str, Depends(is_authenticated)]):
    # Check if advert_id is a valid mongo id
    if not ObjectId.is_valid(advert_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid mongo id received"
        )
    # Delete advert from database
    delete_result = adverts_collection.delete_one(
        filter={"_id": ObjectId(advert_id), "owner": user_id}
    )
    if not delete_result.deleted_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No advert found to delete!")
    # Return response
    return {"message": "Advert deleted succesfully!", "user_id": user_id}


@adverts_router.get(
    "/adverts/user/me",
    tags=["Vendor Dashboard"],
    dependencies=[Depends(has_roles(["vendor", "admin"]))],
)
def get_my_adverts(current_user_id: Annotated[str, Depends(is_authenticated)]):
    # Use the user ID string directly in the database query.
    adverts_query = adverts_collection.find(filter={"owner": current_user_id})
    # Create list
    adverts_list = list(adverts_query)
    # Return response
    return {"data": list(map(replace_mongo_id, adverts_list))}
