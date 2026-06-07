import pymongo
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = pymongo.MongoClient(MONGO_URI)
db = client["MovieBoxBD"]

movies_col = db["movies"]
series_col = db["series"]
ads_col = db["ads"]
admins_col = db["admins"]
states_col = db["user_states"]

if ads_col.count_documents({}) == 0:
    ads_col.insert_one({
        "normal_ad1": "", "normal_ad2": "",
        "adult_ad1": "", "adult_ad2": "",
        "ad_duration": 5, "ads_enabled": True
    })
