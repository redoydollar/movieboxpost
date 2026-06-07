import re
import secrets
from datetime import datetime, timedelta
from pymongo import MongoClient
from config import MONGODB_URI, DB_NAME, VERIFY_EXPIRE_SECONDS

class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DB_NAME]
        self.files = self.db["files"]
        self.users = self.db["users"]
        self.tokens = self.db["tokens"]
        self.settings = self.db["settings"]

        self.files.create_index([("file_name", "text")])
        self.users.create_index("user_id", unique=True)

    def add_file(self, file_id, file_unique_id, file_name, file_size, caption, message_id, channel_id):
        if self.files.find_one({"file_unique_id": file_unique_id}): return False
        self.files.insert_one({"file_id": file_id, "file_unique_id": file_unique_id, "file_name": file_name, "file_size": file_size, "caption": caption or "", "message_id": message_id, "channel_id": channel_id})
        return True

    def search_files(self, query, limit=6):
        regex = re.compile(re.escape(query), re.IGNORECASE)
        results = list(self.files.find({"file_name": regex}).limit(limit))
        if not results: results = list(self.files.find({"$text": {"$search": query}}).limit(limit))
        return results

    def total_files(self): return self.files.count_documents({})

    def add_user(self, user_id, first_name, username=""):
        self.users.update_one({"user_id": user_id}, {"$set": {"first_name": first_name, "username": username}}, upsert=True)

    def is_banned(self, user_id):
        user = self.users.find_one({"user_id": user_id})
        return user and user.get("is_banned", False)

    def ban_user(self, user_id): self.users.update_one({"user_id": user_id}, {"$set": {"is_banned": True}})
    def unban_user(self, user_id): self.users.update_one({"user_id": user_id}, {"$set": {"is_banned": False}})
    def total_users(self): return self.users.count_documents({})

    def create_token(self, user_id, file_id, file_name, is_adult):
        token = secrets.token_hex(16)
        self.tokens.insert_one({"token": token, "user_id": user_id, "file_id": file_id, "file_name": file_name, "is_adult": is_adult, "verified": False, "created_at": datetime.now(), "expires_at": datetime.now() + timedelta(seconds=VERIFY_EXPIRE_SECONDS)})
        return token

    def verify_token(self, token):
        record = self.tokens.find_one({"token": token, "verified": False, "expires_at": {"$gt": datetime.now()}})
        if record:
            time_diff = (datetime.now() - record['created_at']).total_seconds()
            if time_diff < 19: return None # কম সময়ে বাইপাস করলে হবে না
            self.tokens.update_one({"token": token}, {"$set": {"verified": True}})
            return record
        return None

    def get_verified_token(self, token):
        return self.tokens.find_one({"token": token, "verified": True, "expires_at": {"$gt": datetime.now()}})

    def get_setting(self, key, default=""):
        doc = self.settings.find_one({"key": key})
        return doc["value"] if doc else default

    def set_setting(self, key, value):
        self.settings.update_one({"key": key}, {"$set": {"value": value}}, upsert=True)

db = Database()
