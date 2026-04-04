from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
users_collection = db["users"]
bcrypt = Bcrypt()  # instance unique

def create_user(email, hashed_password, name):
    user = {"email": email, "password": hashed_password, "name": name}
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user

def find_user_by_email(email):
    user = users_collection.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user

def check_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return bcrypt.check_password_hash(hashed_password, plain_password)