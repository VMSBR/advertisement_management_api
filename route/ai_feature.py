import os
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from openai import OpenAI
from dotenv import load_dotenv
from typing import Annotated, List

# --- Configuration ---
load_dotenv() # Load environment variables from .env file

# It's best practice to handle the case where the key might be missing
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = OpenAI(api_key=api_key)
ai_router = APIRouter(prefix="/ai", tags=["AI Features"])

# This dependency can be used to inject the OpenAI client
def get_openai_client():
    return client

# --- 1. Image Generation ---
@ai_router.post("/generate-image", summary="Generate an advert image from a description")
async def generate_image_from_description(
    description: Annotated[str, Body(embed=True, description="Detailed description of the advert.")],
    ai_client: Annotated[OpenAI, Depends(get_openai_client)]
):
    """
    Generates a photorealistic image for an advert using DALL-E 3 based on its description.
    """
    try:
        prompt = f"A vibrant, high-quality, photorealistic product photo for an advertisement about: '{description}'. The product should be the central focus, well-lit, and appealing. Minimal text."
       
        response = ai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
        )
        image_url = response.data[0].url
        return {"image_url": image_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")


# --- 2. Description Generation ---
@ai_router.post("/generate-description", summary="Generate a description from a title")
async def generate_description_from_title(
    title: Annotated[str, Body(embed=True, description="Title of the advert.")],
    ai_client: Annotated[OpenAI, Depends(get_openai_client)]
):
    """
    Generates a compelling, marketable description for an advert based on its title.
    """
    try:
        system_prompt = "You are an expert marketing copywriter specializing in agricultural products. Your tone is fresh, appealing, and trustworthy."
        user_prompt = f"Generate a compelling, short (2-3 sentences) product description for an advert titled '{title}'. Highlight freshness and quality."

        response = ai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=150,
        )
        description = response.choices[0].message.content.strip()
        return {"description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate description: {str(e)}")

# --- 3. Related Adverts (Requires a one-time setup) ---
# NOTE: This feature requires you to store 'embeddings' in your database.
#
# Step A: Generate and store an embedding when an advert is CREATED or UPDATED.
# You would call this function inside your create/update advert endpoints.
async def get_embedding(text: str, ai_client: OpenAI) -> List[float]:
    response = ai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small" # A powerful and cost-effective model
    )
    return response.data[0].embedding

# Step B: Create an endpoint to find similar adverts using the stored embeddings.
# This requires a vector index on your MongoDB collection for performance.
# In MongoDB Atlas, go to your collection -> Search Indexes -> Create Search Index -> JSON Editor -> Atlas Vector Search
#
# {
#   "fields": [
#     {
#       "type": "vector",
#       "path": "embedding",
#       "numDimensions": 1536,
#       "similarity": "cosine"
#     }
#   ]
# }
@ai_router.get("/adverts/{advert_id}/related", summary="Find related adverts")
async def find_related_adverts(advert_id: str, adverts_collection): # Inject your collection
    """
    Finds and recommends adverts similar to the one specified by ID.
    This uses vector search on pre-calculated text embeddings.
    """
    from bson import ObjectId

    try:
        target_advert = adverts_collection.find_one({"_id": ObjectId(advert_id)})
        if not target_advert or "embedding" not in target_advert:
            raise HTTPException(status_code=404, detail="Advert or its embedding not found.")

        # Use MongoDB's $vectorSearch for efficient similarity search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_name", # The name of the index you created in Atlas
                    "path": "embedding",
                    "queryVector": target_advert["embedding"],
                    "numCandidates": 100,
                    "limit": 5, # Return the top 5 most similar adverts
                }
            },
            {
                "$project": {
                    "_id": 1, "title": 1, "price": 1, "category": 1, "flyer": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
       
        similar_adverts = list(adverts_collection.aggregate(pipeline))
        # Filter out the original advert itself from the results
        results = [ad for ad in similar_adverts if str(ad["_id"]) != advert_id]

        return {"related_adverts": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve related adverts: {str(e)}")

# --- 4. Price Suggestion ---
@ai_router.post("/suggest-price", summary="Suggest a price range for an advert")
async def suggest_price_for_advert(
    title: Annotated[str, Body(embed=True)],
    category: Annotated[str, Body(embed=True)],
    ai_client: Annotated[OpenAI, Depends(get_openai_client)]
):
    """
    Suggests a competitive price range for an advert based on its title and category.
    """
    try:
        system_prompt = """You are a pricing analyst for an online agricultural marketplace.
        Based on the product title and category, provide a suggested price range.
        Your response MUST be a JSON object with three keys: `min_price` (float), `max_price` (float), and `reasoning` (string).
        Example: {"min_price": 5.50, "max_price": 7.25, "reasoning": "Tomatoes of this type are currently in high demand."}"""
        user_prompt = f"Product Title: '{title}', Category: '{category}'"

        response = ai_client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
       
        price_suggestion = json.loads(response.choices[0].message.content)
        return price_suggestion
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to suggest price: {str(e)}")

# --- 5. Ad Quality Scoring ---
@ai_router.post("/score-quality", summary="Rate the quality of an advert")
async def score_advert_quality(
    title: Annotated[str, Body(embed=True)],
    description: Annotated[str, Body(embed=True)],
    ai_client: Annotated[OpenAI, Depends(get_openai_client)]
):
    """
    Scores the quality of an advert based on its title and description for clarity,
    persuasiveness, and completeness.
    """
    try:
        system_prompt = """You are an ad quality rater. Analyze the given advert title and description.
        Provide a quality score from 1 (poor) to 100 (excellent).
        Your response MUST be a JSON object with two keys: `score` (integer) and `feedback` (string, brief suggestions for improvement).
        Example: {"score": 85, "feedback": "Excellent clarity. Could add more detail about the origin."}"""
        user_prompt = f"Title: '{title}'\nDescription: '{description}'"

        response = ai_client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        quality_score = json.loads(response.choices[0].message.content)
        return quality_score
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to score advert: {str(e)}")

