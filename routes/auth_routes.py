from flask import Blueprint, request, jsonify
from config.db import users_collection
from flask_bcrypt import Bcrypt
from bson import ObjectId

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()

# ✅ SIGNUP
@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json
    required_fields = ["email", "password", "name"]
    
    # Vérifier les champs manquants
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Champs manquants : {', '.join(missing_fields)}"}), 400

    # Vérifier si l'email existe déjà
    if users_collection.find_one({"email": data["email"]}):
        return jsonify({"error": "Email déjà utilisé"}), 400

    # Hasher le mot de passe
    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user_data = {
        "email": data["email"],
        "password": hashed_password,
        "name": data["name"],
        "role": data.get("role", "user")  # par défaut "user"
    }

    result = users_collection.insert_one(user_data)
    return jsonify({"message": "Utilisateur créé", "id": str(result.inserted_id)}), 201


# ✅ LOGIN
@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    required_fields = ["email", "password"]

    # Vérifier les champs manquants
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Champs manquants : {', '.join(missing_fields)}"}), 400

    # Chercher l'utilisateur
    user = users_collection.find_one({"email": data["email"]})
    if not user:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    # Vérifier le mot de passe
    if not bcrypt.check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    return jsonify({
        "message": "Connexion réussie",
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }), 200