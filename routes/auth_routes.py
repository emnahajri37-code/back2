from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
import random
import string
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import resend

auth = Blueprint("auth", __name__)

# ==================== CONNEXION MONGODB ====================
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI non définie")

client = MongoClient(MONGO_URI)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== CONFIGURATION RESEND ====================
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    print("✅ Resend configuré avec succès")
else:
    print("❌ RESEND_API_KEY manquante")

# ==================== FONCTIONS ====================
def generate_verification_code():
    """Génère un code à 6 chiffres"""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(user_email, username, code):
    """Envoie un email via Resend"""
    try:
        if not RESEND_API_KEY:
            print("❌ Clé API Resend manquante")
            return False
        
        params = {
            "from": "IT Support <onboarding@resend.dev>",
            "to": [user_email],
            "subject": "🔐 Votre code de vérification - IT Support System",
            "html": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background-color: #f9f9f9; text-align: center; }}
                    .code {{ font-size: 48px; font-weight: bold; padding: 20px; background-color: #fff; border: 2px dashed #4CAF50; display: inline-block; margin: 20px 0; letter-spacing: 10px; }}
                    .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #888; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>IT Support System</h2>
                    </div>
                    <div class="content">
                        <h3>Bonjour {username} !</h3>
                        <p>Merci de vous être inscrit. Voici votre code de vérification :</p>
                        <div class="code">{code}</div>
                        <p>Ce code expirera dans <strong>10 minutes</strong>.</p>
                        <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 IT Support System</p>
                    </div>
                </div>
            </body>
            </html>
            """,
        }
        
        email = resend.Emails.send(params)
        print(f"✅ Email envoyé via Resend à {user_email} - Code: {code}")
        print(f"📨 Réponse: {email}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Resend: {str(e)}")
        return False

# ==================== ROUTES ====================

@auth.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données JSON manquantes"}), 400
            
        username = data.get('username') or data.get('name') or data.get('fullName')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'it_consultant')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            if existing_user.get('email_verified', False):
                return jsonify({"error": "Cet email est déjà utilisé. Veuillez vous connecter."}), 400
            else:
                users_collection.delete_one({"_id": existing_user['_id']})
                print(f"🗑️ Ancien compte non vérifié supprimé: {email}")
        
        if username and users_collection.find_one({"username": username}):
            return jsonify({"error": "Ce nom d'utilisateur est déjà pris."}), 400
        
        verification_code = generate_verification_code()
        hashed_password = generate_password_hash(password).decode('utf-8')
        
        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "email_verified": False,
            "active": False,
            "verification_code": verification_code,
            "verification_code_expiry": (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Envoi de l'email avec Resend
        send_verification_email(email, username or email, verification_code)
        
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        response_data = {
            "success": True,
            "message": "Inscription réussie ! Un code de vérification vous a été envoyé par email.",
            "token": token,
            "user": {
                "_id": user_id,
                "username": username,
                "email": email,
                "role": role,
                "email_verified": False,
                "active": False
            }
        }
            
        return jsonify(response_data), 201
        
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route("/verify-email", methods=["POST", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        code = data.get('code')
        
        if not email or not code:
            return jsonify({"error": "Email et code requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        if user.get('email_verified'):
            return jsonify({"message": "Email déjà vérifié"}), 200
        
        stored_code = user.get('verification_code')
        expiry_str = user.get('verification_code_expiry')
        
        if not stored_code or stored_code != code:
            return jsonify({"error": "Code de vérification invalide"}), 400
        
        if expiry_str:
            expiry = datetime.datetime.fromisoformat(expiry_str)
            if datetime.datetime.utcnow() > expiry:
                return jsonify({"error": "Code expiré. Veuillez demander un nouveau code."}), 400
        
        users_collection.update_one(
            {"email": email},
            {"$set": {
                "email_verified": True,
                "active": True,
                "verified_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        
        print(f"✅ Email vérifié avec code: {email}")
        
        return jsonify({"message": "Email vérifié avec succès ! Redirection vers la connexion..."}), 200
        
    except Exception as e:
        print(f"❌ Erreur vérification: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route("/resend-code", methods=["POST", "OPTIONS"])
def resend_code():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        if user.get('email_verified'):
            return jsonify({"error": "Email déjà vérifié"}), 400
        
        new_code = generate_verification_code()
        
        users_collection.update_one(
            {"email": email},
            {"$set": {
                "verification_code": new_code,
                "verification_code_expiry": (datetime.datetime.utcnow() + datetime.timedelta(minutes=10)).isoformat()
            }}
        )
        
        send_verification_email(email, user.get('username', email), new_code)
        
        return jsonify({"message": "Nouveau code envoyé avec succès"}), 200
        
    except Exception as e:
        print(f"❌ Erreur renvoi code: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route("/debug-activate", methods=["POST", "OPTIONS"])
def debug_activate():
    """Route pour activer un compte sans email"""
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email requis"}), 400
        
        result = users_collection.update_one(
            {"email": email},
            {"$set": {"email_verified": True, "active": True}}
        )
        
        if result.modified_count:
            print(f"🔧 Compte activé manuellement: {email}")
            return jsonify({"message": f"Compte {email} activé avec succès"}), 200
        else:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
            
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
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user['password'], password):
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        
        if not user.get('email_verified', False):
            return jsonify({
                "error": "Veuillez vérifier votre email avant de vous connecter",
                "email_unverified": True,
                "email": email
            }), 403
        
        if user.get('active') == False:
            return jsonify({"error": "Compte désactivé"}), 401
        
        token = jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user.get('role', 'it_consultant'),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "success": True,
            "message": "Connexion réussie",
            "token": token,
            "user": {
                "_id": str(user['_id']),
                "username": user.get('username'),
                "email": user['email'],
                "role": user.get('role', 'it_consultant'),
                "email_verified": user.get('email_verified', False)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

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