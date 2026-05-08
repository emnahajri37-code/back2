from flask import Blueprint, request, jsonify, current_app
import os
from bson.objectid import ObjectId
from auth_middleware import token_required
import jwt
import datetime
from flask_bcrypt import generate_password_hash
from pymongo import MongoClient
import threading
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

user = Blueprint("user", __name__)

# ==================== CONNEXION MONGODB ====================
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    raise ValueError("❌ MONGO_URI n'est pas définie!")
client = MongoClient(mongo_uri)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== HELPER CORS PREFLIGHT ====================
def _build_cors_preflight_response():
    response = current_app.make_default_options_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# ==================== HELPER: ENVOI EMAIL BREVO ====================
def send_email_brevo(to_email, subject, html_content, text_content):
    """
    Envoi d'email via Brevo dans un thread séparé.
    Corrections apportées :
    - Vérification que BREVO_API_KEY est bien définie
    - html_content ajouté (était absent dans l'original)
    - Meilleure gestion des erreurs avec messages clairs
    """
    def _send():
        api_key = os.environ.get('BREVO_API_KEY')
        if not api_key:
            print("❌ BREVO_API_KEY non définie dans les variables d'environnement")
            return

        try:
            configuration = sib_api_v3_sdk.Configuration()
            configuration.api_key['api-key'] = api_key

            api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
                sib_api_v3_sdk.ApiClient(configuration)
            )
            email_obj = sib_api_v3_sdk.SendSmtpEmail(
                to=[{"email": to_email}],
                sender={"email": "emnasellami18@gmail.com", "name": "IT Support"},
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            api_instance.send_transac_email(email_obj)
            print(f"✅ Email envoyé à {to_email}")

        except ApiException as e:
            # Décode le body pour avoir le message Brevo exact
            try:
                import json
                body = json.loads(e.body)
                print(f"❌ Erreur Brevo API [{e.status}]: {body.get('message', e.body)}")
            except Exception:
                print(f"❌ Erreur Brevo API [{e.status}]: {e.body}")

        except Exception as e:
            print(f"❌ Erreur inattendue lors de l'envoi email: {e}")

    threading.Thread(target=_send, daemon=True).start()

# ==================== HELPER: TOKENS ====================
def generate_reset_token(email):
    payload = {
        'email': email,
        'purpose': 'password_reset',      # ✅ Ajout d'un champ purpose pour valider l'usage
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_reset_token(token):
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        # ✅ Vérifie que le token est bien destiné au reset password
        if payload.get('purpose') != 'password_reset':
            return None
        return payload.get('email')
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def update_user_password(email, hashed_password):
    result = users_collection.update_one(
        {'email': email},
        {'$set': {'password': hashed_password}}
    )
    return result.modified_count > 0

# ==================== CRUD UTILISATEURS ====================

@user.route("/profile", methods=["GET", "OPTIONS"])
@token_required
def get_my_profile(current_user):
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    try:
        user_data = users_collection.find_one({"_id": ObjectId(current_user["_id"])}, {"password": 0})
        if not user_data:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        user_data["_id"] = str(user_data["_id"])
        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user.route("/", methods=["GET", "OPTIONS"])
@token_required
def get_users(current_user):
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    users = list(users_collection.find({}, {"password": 0}))
    for u in users:
        u["_id"] = str(u["_id"])
    return jsonify(users)

@user.route("/<user_id>", methods=["GET", "OPTIONS"])
@token_required
def get_user(current_user, user_id):
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    user_data = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    if not user_data:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    user_data["_id"] = str(user_data["_id"])
    return jsonify(user_data)

@user.route("/<user_id>", methods=["PUT", "OPTIONS"])
@token_required
def update_user(current_user, user_id):
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    data = request.json
    if "password" in data:
        data["password"] = generate_password_hash(data["password"]).decode('utf-8')
    users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": data})
    user_updated = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    user_updated["_id"] = str(user_updated["_id"])
    return jsonify({"message": "Utilisateur mis à jour", "user": user_updated})

@user.route("/<user_id>", methods=["DELETE", "OPTIONS"])
@token_required
def delete_user(current_user, user_id):
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count:
        return jsonify({"message": "Utilisateur supprimé"})
    return jsonify({"error": "Utilisateur non trouvé"}), 404

# ==================== FORGOT PASSWORD ====================
@user.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Corps de requête invalide'}), 400

    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requis'}), 400

    # Réponse neutre pour ne pas révéler si l'email existe
    user_doc = users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if not user_doc:
        return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

    token = generate_reset_token(email)
    base_url = current_app.config.get('BASE_URL', 'http://localhost:3000')
    reset_link = f"{base_url}/reset-password?token={token}"

    send_email_brevo(
        to_email=email,
        subject="Réinitialisation de votre mot de passe",
        html_content=f"""
            <h2>Réinitialisation de mot de passe</h2>
            <p>Bonjour,</p>
            <p>Vous avez demandé à réinitialiser votre mot de passe. Cliquez sur le bouton ci-dessous :</p>
            <a href="{reset_link}" style="
                display:inline-block;padding:12px 24px;background:#4F46E5;
                color:white;text-decoration:none;border-radius:6px;">
                Réinitialiser mon mot de passe
            </a>
            <p>Ce lien expire dans <strong>1 heure</strong>.</p>
            <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
        """,
        text_content=f"Bonjour,\n\nCliquez sur ce lien pour réinitialiser votre mot de passe :\n{reset_link}\n\nExpire dans 1 heure.\n\nSi vous n'avez pas fait cette demande, ignorez cet email."
    )

    return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200


# ==================== RESET PASSWORD ====================
@user.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Corps de requête invalide'}), 400

    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not token or not new_password or not confirm_password:
        return jsonify({'error': 'Token, nouveau mot de passe et confirmation requis'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400

    # ✅ Validation longueur minimale
    if len(new_password) < 8:
        return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400

    email = verify_reset_token(token)
    if not email:
        return jsonify({'error': 'Le lien de réinitialisation est invalide ou a expiré.'}), 400

    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    hashed = generate_password_hash(new_password).decode('utf-8')
    if update_user_password(email, hashed):
        return jsonify({'message': 'Votre mot de passe a été réinitialisé avec succès.'}), 200
    else:
        return jsonify({'error': 'Erreur lors de la mise à jour'}), 500


# ==================== DEBUG TOKEN ====================
@user.route("/debug-token", methods=["OPTIONS", "POST"])
def debug_token():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"error": "Token manquant"}), 400
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256'],
            options={"verify_exp": False}
        )
        return jsonify({
            "valid_signature": True,
            "payload": payload,
            "email_field": payload.get('email'),
            "user_id_field": payload.get('user_id')
        })
    except jwt.InvalidTokenError as e:
        return jsonify({"error": str(e)}), 400