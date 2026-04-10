from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]

users_collection = db["users"]
tickets_collection = db["tickets"]
GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"
