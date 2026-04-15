from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
from flask_bcrypt import Bcrypt
import random

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
users_collection = db["users"]
bcrypt = Bcrypt()

def generate_verification_code():
    """Génère un code aléatoire à 6 chiffres"""
    return str(random.randint(100000, 999999))

def create_user(email, hashed_password, name, role="it_consultant", verification_code=None, verification_code_expiry=None):
    user = {
        "email": email,
        "password": hashed_password,
        "name": name,
        "role": role,
        "email_verified": False,
        "verification_code": verification_code,
        "verification_code_expiry": verification_code_expiry,
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

def check_password(plain_password, hashed_password):
    return bcrypt.check_password_hash(hashed_password, plain_password)

def get_user_by_id(user_id):
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user
    except:
        return None

def verify_user_code(email, code):
    user = users_collection.find_one({"email": email})
    if not user:
        return False
    if (user.get("verification_code") == code and 
        user.get("verification_code_expiry") and 
        datetime.datetime.utcnow() < user["verification_code_expiry"]):
        users_collection.update_one(
            {"email": email},
            {"$set": {"email_verified": True, "verification_code": None, "verification_code_expiry": None}}
        )
        return True
    return False

# Google Auth
def find_user_by_email_for_google(email):
    user = users_collection.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user

def create_google_user(google_id, email, name, picture, role="it_consultant"):
    user = {
        "email": email,
        "name": name,
        "picture": picture,
        "google_id": google_id,
        "role": role,
        "email_verified": True,  # Google vérifie déjà l'email
        "created_at": datetime.datetime.utcnow()
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user

def link_google_account(email, google_id):
    users_collection.update_one({"email": email}, {"$set": {"google_id": google_id}})

def update_user_password(email, hashed_password):
    result = users_collection.update_one({"email": email}, {"$set": {"password": hashed_password}})
    return result.modified_count > 0