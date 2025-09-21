from fastapi import FastAPI, UploadFile
from route.adverts import adverts_router
from route.users import users_router
from pydantic import BaseModel
import cloudinary
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
    
app = FastAPI(
    title="AGROKASA ADVERTISEMENT MANAGEMENT API 🧑‍🌾",
    description="Advertise your agricultural produce here and reach millions of buyers!",
    openapi_tags=tags_metadata)


# Homepage
@app.get("/", tags=["Home"])
def get_home():
    return {"message": " Akwaaba! Welcome to AGROKASA!"}


# include routers
app.include_router(adverts_router)

app.include_router(users_router)