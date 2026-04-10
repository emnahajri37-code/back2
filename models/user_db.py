from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
from datetime import datetime  # ← AJOUTE CET IMPORT

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

def update_user_password(email, hashed_password):
    users_collection.update_one({"email": email}, {"$set": {"password": hashed_password}})

# ========== NOUVELLES FONCTIONS POUR GOOGLE AUTH ==========

def find_user_by_google_id(google_id):
    """Trouver un utilisateur par son ID Google"""
    user = users_collection.find_one({"google_id": google_id})
    if user:
        user["_id"] = str(user["_id"])
    return user

def create_google_user(google_id, email, name, picture):
    """Créer un utilisateur via Google"""
    user = {
        "google_id": google_id,
        "email": email,
        "name": name,
        "picture": picture,
        "email_verified": True,
        "created_at": datetime.now(),
        "password": None  # Pas de mot de passe pour les comptes Google
    }
    result = users_collection.insert_one(user)
    user["_id"] = str(result.inserted_id)
    return user

def link_google_account(email, google_id):
    """Lier un compte Google à un utilisateur existant"""
    result = users_collection.update_one(
        {"email": email}, 
        {"$set": {"google_id": google_id}}
    )
    return result.modified_count > 0

def find_user_by_email_for_google(email):
    """Version de find_user_by_email qui retourne aussi pour update"""
    user = users_collection.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
    return user