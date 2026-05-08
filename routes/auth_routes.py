from flask import Blueprint, request, jsonify, current_app, redirect
from flask_mail import Message
import jwt
import datetime
import secrets
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
# ==================== TEST MAIL ====================

@@auth.route("/test-mail", methods=["GET"])
def test_mail():
    try:
        mail = current_app.extensions.get('mail')
        print(f"MAIL_SERVER: {current_app.config.get('MAIL_SERVER')}")
        print(f"MAIL_USERNAME: {current_app.config.get('MAIL_USERNAME')}")
        print(f"MAIL_PASSWORD set: {bool(current_app.config.get('MAIL_PASSWORD'))}")
        print(f"MAIL_DEFAULT_SENDER: {current_app.config.get('MAIL_DEFAULT_SENDER')}")
        msg = Message(
            subject="Test email",
            recipients=["ticketsystempfe@gmail.com"],
            body="Test Flask-Mail fonctionne."
        )
        mail.send(msg)
        return jsonify({"success": True, "message": "Email envoyé"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# ==================== HELPER ====================

def send_verification_email(email, token):
    mail = current_app.extensions.get('mail')
    if not mail:
        raise RuntimeError("Flask-Mail non initialisé")
    
    base_url = current_app.config.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')
    verify_url = f"{base_url}/verify-email?token={token}"
    
    msg = Message(
        subject="Vérifiez votre adresse email",
        recipients=[email],
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #4F46E5;">Bienvenue !</h2>
            <p>Merci de vous être inscrit. Cliquez sur le bouton ci-dessous pour vérifier votre adresse email :</p>
            <a href="{verify_url}" style="
                display: inline-block;
                padding: 12px 24px;
                background: #4F46E5;
                color: #ffffff;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                margin: 16px 0;
            ">Vérifier mon email</a>
            <p style="color: #666;">Ce lien expire dans <strong>24 heures</strong>.</p>
            <p style="color: #666;">Si vous n'avez pas créé de compte, ignorez cet email.</p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :<br>
                <a href="{verify_url}" style="color: #4F46E5;">{verify_url}</a>
            </p>
        </div>
        """
    )
    mail.send(msg)

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
            if not existing_user.get('email_verified'):
                return jsonify({
                    "error": "Un compte existe déjà avec cet email mais n'est pas encore vérifié.",
                    "needs_verification": True,
                    "email": email
                }), 400
            return jsonify({"error": "Cet email est déjà utilisé. Veuillez vous connecter."}), 400
        
        if username and users_collection.find_one({"username": username}):
            return jsonify({"error": "Ce nom d'utilisateur est déjà pris."}), 400
        
        hashed_password = generate_password_hash(password).decode('utf-8')
        
        verification_token = secrets.token_urlsafe(32)
        token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        
        user_data = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "email_verified": False,
            "active": False,
            "verification_token": verification_token,
            "verification_token_expiry": token_expiry.isoformat()
        }
        
        result = users_collection.insert_one(user_data)
        
        try:
            send_verification_email(email, verification_token)
        except Exception as mail_err:
            users_collection.delete_one({"_id": result.inserted_id})
            print(f"❌ Mail error: {str(mail_err)}")
            return jsonify({"error": f"Impossible d'envoyer l'email de vérification : {str(mail_err)}"}), 500
        
        return jsonify({
            "success": True,
            "message": "Inscription réussie ! Vérifiez votre boîte email pour activer votre compte.",
            "email": email
        }), 201
        
    except Exception as e:
        print(f"❌ Signup error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@auth.route("/verify-email", methods=["GET", "OPTIONS"])
def verify_email():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token manquant"}), 400
    
    user = users_collection.find_one({"verification_token": token})
    if not user:
        return jsonify({"error": "Token invalide ou déjà utilisé"}), 400
    
    expiry = user.get("verification_token_expiry")
    if expiry and datetime.datetime.utcnow() > datetime.datetime.fromisoformat(expiry):
        return jsonify({"error": "Token expiré. Veuillez demander un nouveau lien de vérification."}), 400
    
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "email_verified": True,
            "active": True,
            "verification_token": None,
            "verification_token_expiry": None
        }}
    )
    
    base_url = current_app.config.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')
    return redirect(f"{base_url}/login?verified=true")


@auth.route("/resend-verification", methods=["POST", "OPTIONS"])
def resend_verification():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({"error": "Email requis"}), 400
        
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Aucun compte trouvé avec cet email"}), 404
        
        if user.get('email_verified'):
            return jsonify({"message": "Cet email est déjà vérifié. Vous pouvez vous connecter."}), 200
        
        new_token = secrets.token_urlsafe(32)
        new_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "verification_token": new_token,
                "verification_token_expiry": new_expiry.isoformat()
            }}
        )
        
        try:
            send_verification_email(email, new_token)
        except Exception as mail_err:
            print(f"❌ Mail error: {str(mail_err)}")
            return jsonify({"error": f"Impossible d'envoyer l'email : {str(mail_err)}"}), 500
        
        return jsonify({
            "success": True,
            "message": "Email de vérification renvoyé. Vérifiez votre boîte mail."
        }), 200
        
    except Exception as e:
        print(f"❌ Resend error: {str(e)}")
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
                "error": "Veuillez vérifier votre email avant de vous connecter.",
                "needs_verification": True,
                "email": email
            }), 401
        
        if user.get('active') == False:
            return jsonify({"error": "Compte désactivé. Contactez l'administrateur."}), 401
        
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
                "email_verified": user.get('email_verified', True)
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return jsonify({"error": "Erreur interne du serveur"}), 500


@auth.route("/google", methods=["POST", "OPTIONS"])
def google_login():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    
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