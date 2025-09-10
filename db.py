from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# connect to mongo atlas cluster
mongo_client = MongoClient(os.getenv("MONGO_URI"))


# Access database
advertisement_manager_db = mongo_client["advertisement_manager_db"]

# Pick a connection to operate on
vendors_collection = advertisement_manager_db["vendors"]
adverts_collection = advertisement_manager_db["adverts"]