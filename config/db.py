from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]

users_collection = db["users"]
tickets_collection = db["tickets"]