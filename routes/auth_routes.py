from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import threading
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

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
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# ==================== HELPER: ENVOI EMAIL BREVO ====================
def send_email_brevo(to_email, subject, html_content, text_content):
    """Envoi générique via Brevo API dans un thread séparé."""
    def _send():
        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY')
            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            email = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email}],
                sender={"email": "emnasellami18@gmail.com", "name": "IT Support"},
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            api_instance.send_transac_email(email)
            print(f"✅ Email envoyé à {to_email}")
        except ApiException as e:
            print(f"❌ Erreur Brevo API: {e}")
        except Exception as e:
            print(f"❌ Erreur envoi email: {e}")

    threading.Thread(target=_send).start()

# ==================== HELPER: TOKEN VÉRIFICATION EMAIL ====================
def generate_verification_token(email, user_id):
    payload = {
        'email': email,
        'user_id': user_id,
        'purpose': 'email_verification',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

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

        # ✅ Génération du token JWT principal
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        # ✅ Envoi de l'email de vérification
        verification_token = generate_verification_token(email, user_id)
        base_url = current_app.config.get('BASE_URL', 'http://localhost:3000')
        verify_link = f"{base_url}/verify-email?token={verification_token}"

        send_email_brevo(
            to_email=email,
            subject="Vérifiez votre adresse email",
            html_content=f"""
                <h2>Bienvenue {username or ''} !</h2>
                <p>Merci de vous être inscrit. Cliquez sur le lien ci-dessous pour vérifier votre adresse email :</p>
                <a href="{verify_link}" style="
                    display:inline-block;padding:12px 24px;background:#4F46E5;
                    color:white;text-decoration:none;border-radius:6px;">
                    Vérifier mon email
                </a>
                <p>Ce lien expire dans 24 heures.</p>
                <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
            """,
            text_content=f"Bonjour {username or ''},\n\nVérifiez votre email : {verify_link}\n\nExpire dans 24h."
        )

        return jsonify({
            "message": "Inscription réussie. Vérifiez votre email.",
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


# ==================== VÉRIFICATION EMAIL ====================
@auth.route("/verify-email", methods=["GET"])
def verify_email():
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token manquant"}), 400

    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])

        if payload.get('purpose') != 'email_verification':
            return jsonify({"error": "Token invalide"}), 400

        email = payload.get('email')
        user = users_collection.find_one({"email": email})

        if not user:
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        if user.get('email_verified'):
            return jsonify({"message": "Email déjà vérifié."}), 200

        users_collection.update_one(
            {"email": email},
            {"$set": {"email_verified": True}}
        )
        return jsonify({"message": "Email vérifié avec succès !"}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Le lien de vérification a expiré. Veuillez vous réinscrire ou demander un nouveau lien."}), 400
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token invalide"}), 400


# ==================== RENVOYER L'EMAIL DE VÉRIFICATION ====================
@auth.route("/resend-verification", methods=["POST"])
def resend_verification():
    """Permet de renvoyer l'email de vérification si l'utilisateur ne l'a pas reçu."""
    try:
        data = request.get_json()
        email = data.get('email')
        if not email:
            return jsonify({"error": "Email requis"}), 400

        user = users_collection.find_one({"email": email})
        if not user:
            # Réponse neutre pour ne pas révéler l'existence du compte
            return jsonify({"message": "Si cet email est enregistré, un lien sera envoyé."}), 200

        if user.get('email_verified'):
            return jsonify({"message": "Cet email est déjà vérifié."}), 200

        user_id = str(user['_id'])
        verification_token = generate_verification_token(email, user_id)
        base_url = current_app.config.get('BASE_URL', 'http://localhost:3000')
        verify_link = f"{base_url}/verify-email?token={verification_token}"

        send_email_brevo(
            to_email=email,
            subject="Vérifiez votre adresse email",
            html_content=f"""
                <h2>Vérification de votre email</h2>
                <p>Cliquez sur le lien ci-dessous :</p>
                <a href="{verify_link}" style="
                    display:inline-block;padding:12px 24px;background:#4F46E5;
                    color:white;text-decoration:none;border-radius:6px;">
                    Vérifier mon email
                </a>
                <p>Ce lien expire dans 24 heures.</p>
            """,
            text_content=f"Vérifiez votre email : {verify_link}\n\nExpire dans 24h."
        )

        return jsonify({"message": "Email de vérification renvoyé."}), 200

    except Exception as e:
        print(f"❌ Resend verification error: {str(e)}")
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

        # ⚠️ Optionnel : bloquer la connexion si email non vérifié
        # if not user.get('email_verified'):
        #     return jsonify({"error": "Veuillez vérifier votre email avant de vous connecter."}), 403

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
                "email_verified": True,   # ✅ Google garantit l'email
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
                    "error": f"Cet email est déjà utilisé pour un compte {user.get('role')}. Veuillez vous connecter avec celui-ci."
                }), 400

            if not user.get('google_id'):
                users_collection.update_one({"email": email}, {"$set": {"google_id": google_id}})

            # ✅ Marquer email_verified si connexion Google sur compte existant
            if not user.get('email_verified'):
                users_collection.update_one({"email": email}, {"$set": {"email_verified": True}})

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
                "role": user_role,
                "email_verified": True
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