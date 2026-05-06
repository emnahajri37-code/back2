from functools import wraps
from flask import request, jsonify, g, current_app
import jwt
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

# ==================== CONFIGURATION ====================
SECRET_KEY = os.environ.get('SECRET_KEY', 'ma_super_cle_secrete_pour_les_tokens_12345!')
client = MongoClient(os.environ.get('MONGO_URI'))
db = client["pfe_db"]
users_collection = db["users"]

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"message": "Token manquant"}), 401

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"message": "Format du token invalide"}), 401

        token = parts[1]

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = data.get("user_id")
            if not user_id:
                return jsonify({"message": "Token invalide (pas d'identifiant)"}), 401

            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return jsonify({"message": "Utilisateur introuvable"}), 401

            if "role" not in user:
                user["role"] = "it_consultant"

            g.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expiré"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Token invalide: {str(e)}"}), 401

        return f(g.current_user, *args, **kwargs)
    return decorated