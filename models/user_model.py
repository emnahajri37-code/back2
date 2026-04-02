from config.db import users_collection
from bson import ObjectId
from werkzeug.security import generate_password_hash

# ✅ CREATE USER
def create_user(data):
    user = {
        "name": data["name"],
        "email": data["email"],
        "password": generate_password_hash(data["password"]),
        "role": data["role"]
    }
    result = users_collection.insert_one(user)
    return str(result.inserted_id)


# ✅ GET ALL USERS
def get_all_users():
    users = []
    for u in users_collection.find():
        u["_id"] = str(u["_id"])
        users.append(u)
    return users


# ✅ GET ONE USER
def get_user_by_id(user_id):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
    return user


# ✅ UPDATE USER
def update_user(user_id, data):
    update_data = {}

    if "name" in data:
        update_data["name"] = data["name"]
    if "email" in data:
        update_data["email"] = data["email"]
    if "role" in data:
        update_data["role"] = data["role"]
    if "password" in data:
        update_data["password"] = generate_password_hash(data["password"])

    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )


# ✅ DELETE USER
def delete_user(user_id):
    users_collection.delete_one({"_id": ObjectId(user_id)})