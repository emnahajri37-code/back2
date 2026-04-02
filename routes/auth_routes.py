from flask import Blueprint, request, jsonify
from models.user_model import create_user
from config.db import users_collection
from werkzeug.security import check_password_hash

auth = Blueprint("auth", __name__)

# ✅ SIGNUP
@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json
    user_id = create_user(data)

    return jsonify({
        "message": "User créé avec succès",
        "id": user_id
    })


# ✅ LOGIN
@auth.route("/login", methods=["POST"])
def login():
    data = request.json

    user = users_collection.find_one({"email": data["email"]})

    if user and check_password_hash(user["password"], data["password"]):
        return jsonify({
            "message": "Login réussi",
            "user": {
                "id": str(user["_id"]),
                "name": user["name"],
                "role": user["role"]
            }
        })

    return jsonify({"error": "Email ou mot de passe incorrect"}), 401