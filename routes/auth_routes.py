from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
import jwt
import datetime
import random
import string
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

# ==================== FONCTIONS ====================
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(user_email, username, code):
    try:
        msg = Message(
            subject="🔐 Votre code de vérification",
            recipients=[user_email],
            html=f"""
            <h2>Bonjour {username} !</h2>
            <p>Voici votre code de vérification : <strong>{code}</strong></p>
            <p>Ce code expire dans 10 minutes.</p>
            """
        )
        mail = current_app.extensions.get('mail')
        mail.send(msg)
        print(f"✅ Email envoyé à {user_email}")
        return True
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return False

# ==================== ROUTES ====================

@auth.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    try:
        data = request.get_json()
        username = data.get('name') or data.get('fullName')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'it_consultant')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        existing = users_collection.find_one({"email": email})
        if existing and existing.get('email_verified'):
            return jsonify({"error": "Email déjà utilisé"}), 400
        elif existing and not existing.get('email_verified'):
            users_collection.delete_one({"_id": existing['_id']})
        
        code = generate_verification_code()
        hashed = generate_password_hash(password).decode('utf-8')
        
        user_data = {
            "username": username,
            "email": email,
            "password": hashed,
            "role": role,
            "email_verified": False,
            "active": False,
            "verification_code": code,
            "verification_code_expiry": (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()
        }
        result = users_collection.insert_one(user_data)
        
        send_verification_email(email, username or email, code)
        
        token = jwt.encode({
            'user_id': str(result.inserted_id),
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "success": True,
            "message": "Inscription réussie ! Vérifiez vos emails",
            "token": token,
            "user": {"_id": str(result.inserted_id), "username": username, "email": email, "role": role}
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth.route("/verify-email", methods=["POST", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        if user.get('verification_code') != code:
            return jsonify({"error": "Code invalide"}), 400
        users_collection.update_one({"email": email}, {"$set": {"email_verified": True, "active": True}})
        return jsonify({"message": "Email vérifié avec succès"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user['password'], password):
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        if not user.get('email_verified'):
            return jsonify({"error": "Veuillez vérifier votre email", "email_unverified": True}), 403
        token = jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user.get('role', 'it_consultant'),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        return jsonify({
            "success": True,
            "token": token,
            "user": {"_id": str(user['_id']), "username": user.get('username'), "email": user['email'], "role": user.get('role')}
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== ROUTE GOOGLE OAUTH ====================
@auth.route("/google", methods=["POST", "OPTIONS"])
def google_login():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        id_token_credential = data.get('credential') or data.get('id_token')
        
        if not id_token_credential:
            return jsonify({"error": "Token Google manquant"}), 400
        
        # Vérification du token Google
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"
        info = id_token.verify_oauth2_token(id_token_credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        
        email = info.get('email')
        name = info.get('name')
        role = data.get('role', 'developer')
        
        if not email:
            return jsonify({"error": "Email non fourni par Google"}), 400
        
        # Vérifie si l'utilisateur existe
        user = users_collection.find_one({"email": email})
        
        if not user:
            # Création d'un nouvel utilisateur
            user_data = {
                "username": name,
                "email": email,
                "role": role,
                "email_verified": True,
                "active": True,
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            result = users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            user_role = role
            user_username = name
        else:
            # L'email existe déjà → vérifie le rôle
            if user.get('role') != role:
                return jsonify({
                    "error": f"Cet email est déjà utilisé pour un compte {user.get('role')}. Veuillez vous connecter avec celui-ci."
                }), 400
            user_id = str(user['_id'])
            user_role = user.get('role')
            user_username = user.get('username')
        
        # Génération du token JWT
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
        return jsonify({"error": str(e)}), 500

# ==================== ROUTES ME ET CHECK-EMAIL ====================
@auth.route("/me", methods=["GET", "OPTIONS"])
def get_me():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token manquant"}), 401
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return jsonify({"error": "Format token invalide"}), 401
    token = parts[1]
    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user = users_collection.find_one({"_id": ObjectId(data['user_id'])}, {"password": 0})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 401

@auth.route("/check-email", methods=["POST", "OPTIONS"])
def check_email():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({"error": "Email requis"}), 400
        user = users_collection.find_one({"email": email})
        return jsonify({
            "exists": user is not None,
            "email": email,
            "role": user.get('role') if user else None,
            "verified": user.get('email_verified') if user else False
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500