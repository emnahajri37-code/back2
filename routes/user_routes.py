from flask import Blueprint, request, jsonify, g
from pymongo import MongoClient
from bson.objectid import ObjectId
from auth_middleware import token_required

user = Blueprint("user", __name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
users_collection = db["users"]

# ===========================
# GET ALL USERS
# ===========================
@user.route("/", methods=["GET"])
@token_required
def get_users(current_user):
    users = list(users_collection.find({}, {"password": 0}))  # ne pas renvoyer les mots de passe
    for u in users:
        u["_id"] = str(u["_id"])
    return jsonify(users)

# ===========================
# GET USER BY ID
# ===========================
@user.route("/<user_id>", methods=["GET"])
@token_required
def get_user(current_user, user_id):
    user_data = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user_data:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    user_data["_id"] = str(user_data["_id"])
    return jsonify(user_data)

# ===========================
# UPDATE USER
# ===========================
@user.route("/<user_id>", methods=["PUT"])
@token_required
def update_user(current_user, user_id):
    data = request.json
    if "password" in data:
        from flask_bcrypt import generate_password_hash
        data["password"] = generate_password_hash(data["password"]).decode('utf-8')
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": data})
    user_updated = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    user_updated["_id"] = str(user_updated["_id"])
    return jsonify({"message": "Utilisateur mis à jour", "user": user_updated})

# ===========================
# DELETE USER
# ===========================
@user.route("/<user_id>", methods=["DELETE"])
@token_required
def delete_user(current_user, user_id):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count:
        return jsonify({"message": "Utilisateur supprimé"})
    return jsonify({"error": "Utilisateur non trouvé"}), 404