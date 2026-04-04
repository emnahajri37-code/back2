from functools import wraps
from flask import request, jsonify, g
import jwt
from pymongo import MongoClient
from bson.objectid import ObjectId

SECRET_KEY = "secret123"

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
users_collection = db["users"]

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print("\n=== DÉBUT MIDDLEWARE ===")
        auth_header = request.headers.get("Authorization", None)
        print(f"Authorization header: {auth_header}")

        if not auth_header:
            print("❌ Aucun header Authorization")
            return jsonify({"message": "Token manquant"}), 401

        parts = auth_header.split()
        print(f"Parts: {parts}")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            print("❌ Format invalide (doit être 'Bearer <token>')")
            return jsonify({"message": "Format du token invalide"}), 401

        token = parts[1]
        print(f"Token extrait (premiers 20 caractères): {token[:20]}...")

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            print(f"✅ Token décodé: {data}")
            user_id = data.get("user_id")  # doit correspondre à la clé utilisée dans auth_routes
            print(f"user_id extrait: {user_id}")
            if not user_id:
                print("❌ Pas de 'user_id' dans le token")
                return jsonify({"message": "Token invalide (pas d'identifiant)"}), 401

            user = users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                print(f"❌ Utilisateur non trouvé pour _id: {user_id}")
                return jsonify({"message": "Utilisateur introuvable"}), 401

            print(f"✅ Utilisateur trouvé: {user.get('email')}")
            g.current_user = user
        except jwt.ExpiredSignatureError:
            print("❌ Token expiré")
            return jsonify({"message": "Token expiré"}), 401
        except jwt.InvalidTokenError as e:
            print(f"❌ Token invalide: {e}")
            return jsonify({"message": "Token invalide"}), 401

        print("=== FIN MIDDLEWARE, appel de la route ===\n")
        return f(g.current_user, *args, **kwargs)
    return decorated