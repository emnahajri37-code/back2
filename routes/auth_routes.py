from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

auth = Blueprint("auth", __name__)

# ==================== CONNEXION MONGODB ====================
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI non définie")

client = MongoClient(MONGO_URI)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== ROUTES ====================

@auth.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        username = data.get('username') or data.get('name') or data.get('fullName')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'it_consultant')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        # 🔒 Vérification email unique
        if users_collection.find_one({"email": email}):
            return jsonify({"error": "Cet email est déjà utilisé. Veuillez vous connecter."}), 400
        
        if username and users_collection.find_one({"username": username}):
            return jsonify({"error": "Ce nom d'utilisateur est déjà pris."}), 400
        
        hashed_password = generate_password_hash(password).decode('utf-8')
        
        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "email_verified": False,
            "active": True
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "message": "Inscription réussie",
            "token": token,
            "user": {
                "_id": user_id,
                "username": username,
                "email": email,
                "role": role
            }
        }), 201
        
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

@auth.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user['password'], password):
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        
        if user.get('active') == False:
            return jsonify({"error": "Compte désactivé"}), 401
        
        token = jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user.get('role', 'it_consultant'),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "message": "Connexion réussie",
            "token": token,
            "user": {
                "_id": str(user['_id']),
                "username": user.get('username'),
                "email": user['email'],
                "role": user.get('role', 'it_consultant')
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500

@auth.route("/google", methods=["POST"])
def google_login():
    try:
        data = request.get_json()
        id_token_credential = data.get('id_token') or data.get('credential')
        
        if not id_token_credential:
            return jsonify({"error": "Token Google manquant"}), 400
        
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"
        try:
            info = id_token.verify_oauth2_token(id_token_credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        except Exception as e:
            return jsonify({"error": "Token Google invalide"}), 400
        
        email = info.get('email')
        name = info.get('name')
        google_id = info.get('sub')
        role = data.get('role', 'developer')
        
        if not email:
            return jsonify({"error": "Email non fourni par Google"}), 400
        
        user = users_collection.find_one({"email": email})
        
        if not user:
            # ➕ Création d'un NOUVEAU compte (email inconnu)
            user_data = {
                "username": name,
                "email": email,
                "google_id": google_id,
                "role": role,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "email_verified": True,
                "active": True
            }
            result = users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            user_role = role
            user_username = name
        else:
            # 🔒 L'email existe déjà → on vérifie les rôles
            if user.get('role') != role:
                return jsonify({
                    "success": False,
                    "error": f"Cet email est déjà utilisé pour un compte {user.get('role')}. Veuillez vous connecter avec celui-ci."
                }), 400
            
            # Mise à jour du google_id si absent
            if not user.get('google_id'):
                users_collection.update_one({"email": email}, {"$set": {"google_id": google_id}})
            
            user_id = str(user['_id'])
            user_role = user.get('role')
            user_username = user.get('username', name)
        
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': user_role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "success": True,
            "message": "Connexion Google réussie",
            "token": token,
            "user": {
                "_id": user_id,
                "username": user_username,
                "email": email,
                "role": user_role
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Google auth error: {str(e)}")
        return jsonify({"success": False, "error": "Erreur d'authentification Google"}), 500
@auth.route("/me", methods=["GET"])
def get_me():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token manquant"}), 401
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify({"error": "Format token invalide"}), 401
    
    token = parts[1]
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({"error": "Token invalide"}), 401
        
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
        
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 401

@auth.route("/check-email", methods=["POST"])
def check_email():
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({"error": "Email requis"}), 400
        
        user = users_collection.find_one({"email": email})
        return jsonify({
            "exists": user is not None,
            "email": email,
            "role": user.get('role') if user else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500