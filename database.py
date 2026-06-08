from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db["users"]

def save_thumbnail(user_id, file_id):
    users_col.update_one({"user_id": user_id}, {"$set": {"thumbnail": file_id}}, upsert=True)

def get_thumbnail(user_id):
    user = users_col.find_one({"user_id": user_id})
    if user:
        return user.get("thumbnail")
    return None

def delete_thumbnail(user_id):
    users_col.update_one({"user_id": user_id}, {"$unset": {"thumbnail": ""}})
