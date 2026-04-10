from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
import os

bcrypt = Bcrypt()

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
users_collection = db["users"]

def create_user(email, hashed_password, name, role="it_consultant"):
    user = {
        "email": email,
        "password": hashed_password,
        "name": name,
        "role": role,
        "created_at": datetime.datetime.utcnow() 
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user


def find_user_by_email(email):
    user = users_collection.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user

def find_user_by_google_id(google_id):
    user = users_collection.find_one({"google_id": google_id})
    if user:
        user["_id"] = str(user["_id"])
    return user

def find_user_by_email_for_google(email):
    return users_collection.find_one({"email": email})

def link_google_account(email, google_id):
    users_collection.update_one({"email": email}, {"$set": {"google_id": google_id}})

def create_google_user(google_id, email, name, picture):
    user = {
        "email": email,
        "name": name,
        "picture": picture,
        "google_id": google_id,
        "role": "it_consultant",  # valeur par défaut
        "created_at": datetime.utcnow()
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user

def check_password(plain_password, hashed_password):
    return bcrypt.check_password_hash(hashed_password, plain_password)

def update_user(user_id, update_data):
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})

def get_user_by_id(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user