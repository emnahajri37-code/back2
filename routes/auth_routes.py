from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

auth = Blueprint("auth", __name__)

# ==================== CONNEXION MONGODB ====================
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI non définie")

client = MongoClient(MONGO_URI)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== HELPER CORS PREFLIGHT ====================
def _build_cors_preflight_response():
    response = current_app.make_default_options_response()
    response.headers.add("Access-Control-Allow-Origin", "https://sparkling-wisp-363896.netlify.app")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# ==================== FONCTIONS EMAIL ====================
def generate_verification_token(email):
    """Génère un token sécurisé pour la vérification email"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='email-verification')

def verify_verification_token(token, expiration=86400):
    """Vérifie le token et retourne l'email si valide"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt='email-verification', max_age=expiration)
        return email
    except Exception:
        return None

def send_verification_email(user_email, username):
    """Envoie l'email de vérification avec lien"""
    try:
        # Vérifier que la configuration email est présente
        if not current_app.config.get('MAIL_USERNAME') or not current_app.config.get('MAIL_PASSWORD'):
            print("❌ Configuration email manquante dans app.config")
            return False
        
        token = generate_verification_token(user_email)
        frontend_url = current_app.config.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')
        verification_url = f"{frontend_url}/verify-email?token={token}"
        
        msg = Message(
            subject="🔐 Vérifiez votre adresse email - IT Support System",
            recipients=[user_email],
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 30px; background-color: #f9f9f9; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #888; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>Bienvenue sur IT Support System</h2>
                    </div>
                    <div class="content">
                        <h3>Bonjour {username} !</h3>
                        <p>Merci de vous être inscrit sur notre plateforme de gestion de tickets IT.</p>
                        <p>Pour activer votre compte, veuillez vérifier votre adresse email :</p>
                        
                        <div style="text-align: center;">
                            <a href="{verification_url}" class="button">✅ Vérifier mon email</a>
                        </div>
                        
                        <p style="background-color: #eee; padding: 10px; border-radius: 3px; word-break: break-all;">
                            Lien : {verification_url}
                        </p>
                        
                        <p><strong>⚠️ Ce lien expirera dans 24 heures.</strong></p>
                        <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2025 IT Support System</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            body=f"""
Bienvenue sur IT Support System !

Bonjour {username},

Merci de vous être inscrit. Pour activer votre compte, cliquez sur ce lien :

{verification_url}

Ce lien expirera dans 24 heures.

Si vous n'avez pas créé ce compte, ignorez cet email.

---
© 2025 IT Support System
            """,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config.get('MAIL_USERNAME'))
        )
        
        mail = current_app.extensions['mail']
        mail.send(msg)
        print(f"✅ Email de vérification envoyé à {user_email}")
        return True
    except Exception as e:
        print(f"❌ Erreur envoi email à {user_email}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# ==================== ROUTES ====================

@auth.route("/signup", methods=["POST", "OPTIONS"])
def signup():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        username = data.get('username') or data.get('name') or data.get('fullName')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'it_consultant')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        # Vérifier si l'utilisateur existe déjà
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({"error": "Cet email est déjà utilisé. Veuillez vous connecter."}), 400
        
        if username and users_collection.find_one({"username": username}):
            return jsonify({"error": "Ce nom d'utilisateur est déjà pris."}), 400
        
        # Hacher le mot de passe
        hashed_password = generate_password_hash(password).decode('utf-8')
        
        # Créer l'utilisateur
        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "email_verified": False,
            "active": False,  # Compte inactif jusqu'à vérification email
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Envoyer l'email de vérification
        email_sent = send_verification_email(email, username or email)
        
        # Générer un token JWT
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        response_data = {
            "message": "Inscription réussie ! Un email de vérification vous a été envoyé." if email_sent else "Inscription réussie mais l'email n'a pas pu être envoyé. Veuillez contacter le support.",
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
        
        if not email_sent:
            response_data["warning"] = "Configuration email incomplète. Contactez l'administrateur."
            
        return jsonify(response_data), 201
        
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Erreur interne du serveur"}), 500

@auth.route("/verify-email", methods=["GET", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    try:
        token = request.args.get('token')
        if not token:
            return jsonify({"error": "Token de vérification manquant"}), 400
        
        # Vérifier le token
        email = verify_verification_token(token)
        if not email:
            return jsonify({"error": "Lien de vérification invalide ou expiré"}), 400
        
        # Trouver l'utilisateur
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        
        if user.get('email_verified'):
            return jsonify({"message": "Email déjà vérifié. Vous pouvez vous connecter."}), 200
        
        # Activer le compte
        users_collection.update_one(
            {"email": email},
            {"$set": {
                "email_verified": True,
                "active": True,
                "verified_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        
        print(f"✅ Email vérifié: {email}")
        
        frontend_url = current_app.config.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')
        return jsonify({
            "message": "Email vérifié avec succès ! Vous pouvez maintenant vous connecter.",
            "redirect_url": f"{frontend_url}/login?verified=true"
        }), 200
        
    except Exception as e:
        print(f"❌ Erreur vérification: {str(e)}")
        return jsonify({"error": "Erreur lors de la vérification"}), 500

@auth.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user or not check_password_hash(user['password'], password):
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        
        # Vérifier si l'email est vérifié
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
        return jsonify({"error": "Erreur interne du serveur"}), 500

@auth.route("/google", methods=["POST", "OPTIONS"])
def google_login():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    try:
        data = request.get_json()
        id_token_credential = data.get('id_token') or data.get('credential')
        
        if not id_token_credential:
            return jsonify({"error": "Token Google manquant"}), 400
        
        # Vérification du token Google
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"
        try:
            info = id_token.verify_oauth2_token(id_token_credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        except Exception as e:
            print(f"❌ Google token verification failed: {str(e)}")
            return jsonify({"error": "Token Google invalide"}), 400
        
        email = info.get('email')
        name = info.get('name')
        google_id = info.get('sub')
        role = data.get('role', 'developer')
        
        if not email:
            return jsonify({"error": "Email non fourni par Google"}), 400
        
        user = users_collection.find_one({"email": email})
        
        if not user:
            # Création nouvel utilisateur
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
            # Vérification rôle
            if user.get('role') != role:
                return jsonify({
                    "success": False,
                    "error": f"Cet email est déjà utilisé pour un compte {user.get('role')}."
                }), 400
            
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

@auth.route("/me", methods=["GET", "OPTIONS"])
def get_me():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
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
        return _build_cors_preflight_response()
    
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

@auth.route("/resend-verification", methods=["POST", "OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
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
        
        # Renvoyer l'email
        email_sent = send_verification_email(email, user.get('username', email))
        
        if email_sent:
            return jsonify({"message": "Email de vérification renvoyé"}), 200
        else:
            return jsonify({"error": "Impossible d'envoyer l'email"}), 500
        
    except Exception as e:
        print(f"❌ Erreur renvoi: {str(e)}")
        return jsonify({"error": "Erreur interne"}), 500