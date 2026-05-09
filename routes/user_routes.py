from flask import Blueprint, request, jsonify, current_app
import os
from bson.objectid import ObjectId
from auth_middleware import token_required
import jwt
import datetime
from flask_bcrypt import generate_password_hash
from pymongo import MongoClient
import resend

user = Blueprint("user", __name__)

# ==================== CONNEXION MONGODB ====================
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    raise ValueError("❌ MONGO_URI n'est pas définie!")
client = MongoClient(mongo_uri)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== CONFIGURATION RESEND ====================
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    print("✅ Resend configuré")

# ==================== HELPER: TOKENS ====================
def generate_reset_token(email):
    payload = {
        'email': email,
        'purpose': 'password_reset',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_reset_token(token):
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
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

# ==================== GET ALL USERS ====================
@user.route("/", methods=["GET"])
@token_required
def get_users(current_user):
    users = list(users_collection.find({}, {"password": 0}))
    for u in users:
        u["_id"] = str(u["_id"])
    return jsonify(users), 200

# ==================== GET MY PROFILE ====================
@user.route("/profile", methods=["GET"])
@token_required
def get_my_profile(current_user):
    try:
        user_data = users_collection.find_one({"_id": ObjectId(current_user["_id"])}, {"password": 0})
        if not user_data:
            return jsonify({"error": "Utilisateur non trouvé"}), 404
        user_data["_id"] = str(user_data["_id"])
        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== GET / PUT / DELETE USER ====================
@user.route("/<user_id>", methods=["GET", "PUT", "DELETE"])
@token_required
def user_by_id(current_user, user_id):
    if request.method == "GET":
        try:
            user_data = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
            if not user_data:
                return jsonify({"error": "Utilisateur non trouvé"}), 404
            user_data["_id"] = str(user_data["_id"])
            return jsonify(user_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "PUT":
        try:
            if current_user.get('role') not in ['admin', 'it_consultant'] and str(current_user.get('_id')) != user_id:
                return jsonify({"error": "Action non autorisée"}), 403

            data = request.json
            if not data:
                return jsonify({"error": "Données manquantes"}), 400

            allowed_fields = ["username", "name", "email", "phone", "location"]
            update_data = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

            if "password" in data and data["password"]:
                if len(data["password"]) < 6:
                    return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
                update_data["password"] = generate_password_hash(data["password"]).decode('utf-8')

            if not update_data:
                return jsonify({"error": "Aucun champ valide à mettre à jour"}), 400

            result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 0:
                return jsonify({"error": "Utilisateur non trouvé"}), 404

            user_updated = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
            if user_updated:
                user_updated["_id"] = str(user_updated["_id"])
            return jsonify({"message": "Utilisateur mis à jour", "user": user_updated}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        try:
            if current_user.get('role') not in ['admin', 'it_consultant']:
                return jsonify({"error": "Action non autorisée. Droits administrateur requis."}), 403

            current_user_id = str(current_user.get('_id') or current_user.get('user_id', ''))
            if current_user_id == user_id:
                return jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte"}), 400

            result = users_collection.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count:
                return jsonify({"message": "Utilisateur supprimé avec succès"}), 200
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ==================== FORGOT PASSWORD ====================
@user.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Corps de requête invalide'}), 400

    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requis'}), 400

    user_doc = users_collection.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if not user_doc:
        return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

    token = generate_reset_token(email)
    base_url = current_app.config.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')
    reset_link = f"{base_url}/reset-password?token={token}"

    try:
        if RESEND_API_KEY:
            resend.Emails.send({
                "from": "IT Support <onboarding@resend.dev>",
                "to": [email],
                "subject": "Réinitialisation de votre mot de passe",
                "html": f"""
                    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;padding:32px;">
                        <h2 style="color:#4F46E5;">Réinitialisation de mot de passe</h2>
                        <p>Cliquez sur le bouton ci-dessous pour réinitialiser votre mot de passe :</p>
                        <a href="{reset_link}" style="display:inline-block;padding:12px 24px;background:#4F46E5;color:white;text-decoration:none;border-radius:6px;">
                            Réinitialiser mon mot de passe
                        </a>
                        <p style="color:#6b7280;font-size:14px;margin-top:16px;">Ce lien expire dans 1 heure.</p>
                    </div>
                """
            })
            print(f"✅ Email envoyé à {email}")
        else:
            print(f"🔑 Reset link: {reset_link}")
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")

    return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

# ==================== RESET PASSWORD ====================
@user.route("/reset-password", methods=["POST"])
def reset_password():
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
    return jsonify({'error': 'Erreur lors de la mise à jour'}), 500

# ==================== DEBUG TOKEN ====================
@user.route("/debug-token", methods=["POST"])
def debug_token():
    data = request.get_json()
    token = data.get('token')
    if not token:
        return jsonify({"error": "Token manquant"}), 400
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'], options={"verify_exp": False})
        return jsonify({
            "valid_signature": True,
            "payload": payload,
            "email_field": payload.get('email'),
            "user_id_field": payload.get('user_id')
        })
    except jwt.InvalidTokenError as e:
        return jsonify({"error": str(e)}), 400