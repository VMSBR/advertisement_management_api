import os
from dotenv import load_dotenv
import google.genai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set in .env")

genai_client = genai.Client(api_key=api_key)

def replace_mongo_id(doc):
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    return doc
