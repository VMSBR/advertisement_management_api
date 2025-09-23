import os
import base64
from io import BytesIO
from fastapi import APIRouter, HTTPException, Body
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from typing import Annotated



load_dotenv() 

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    raise ValueError("HF_TOKEN environment variable not set.")

# Initialize the Hugging Face Inference Client
client = InferenceClient(token=hf_token)

ai_router = APIRouter(prefix="/ai", tags=["🤗AI Features (Hugging Face)"])

# Image Generation
@ai_router.post("/generate-image", summary="Generate an advert image from a description")
def generate_image_from_description(
    description: Annotated[str, Body(embed=True, description="Detailed description of the advert.")]
):
    try:
        prompt = f"advertisement photo, {description}, high quality, high resolution, professional product photography"
       
        image_bytes = client.text_to_image(
            prompt,
            model="stabilityai/stable-diffusion-xl-base-1.0"
        )
        
        buffered = BytesIO()
        image_bytes.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
       
        return {
            "image_base64": img_str,
            "format": "jpeg"
        }
    except Exception as e:
        # Check for specific Hugging Face errors
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")