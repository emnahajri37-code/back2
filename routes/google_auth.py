from flask import Blueprint, request, jsonify, current_app, redirect
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import jwt
import datetime
from pymongo import MongoClient
import os

google_auth = Blueprint("google_auth", __name__)

# Connexion MongoDB
MONGO_URI = os.environ.get('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client["pfe_db"]
users_collection = db["users"]

GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"

@google_auth.route("/auth/google", methods=["POST"])
def google_login():
    try:
        data = request.get_json()
        token = data.get('credential')
        
        if not token:
            return jsonify({"error": "Token Google manquant"}), 400
        
        # Vérifie le token Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        google_id = idinfo.get('sub')
        
        # Vérifie si l'utilisateur existe
        user = users_collection.find_one({"email": email})
        
        if not user:
            # Crée un nouvel utilisateur
            user_data = {
                "username": name,
                "email": email,
                "picture": picture,
                "google_id": google_id,
                "role": "it_consultant",
                "created_at": datetime.datetime.utcnow().isoformat(),
                "email_verified": True
            }
            result = users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            user_role = "it_consultant"
        else:
            user_id = str(user['_id'])
            user_role = user.get('role', 'it_consultant')
        
        # Génère ton token JWT
        jwt_token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': user_role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "message": "Connexion Google réussie",
            "token": jwt_token,
            "user": {
                "_id": user_id,
                "username": name,
                "email": email,
                "role": user_role,
                "picture": picture
            }
        }), 200
        
    except Exception as e:
        print(f"Erreur Google: {str(e)}")
        return jsonify({"error": str(e)}), 500