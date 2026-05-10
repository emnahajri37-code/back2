from flask import Blueprint, request, jsonify, current_app
import os
from bson.objectid import ObjectId
import jwt
import datetime
from flask_bcrypt import generate_password_hash
from pymongo import MongoClient
import resend

user = Blueprint("user", __name__)

# ==================== CONNEXION MONGODB ====================
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    raise ValueError("❌ MONGO_URI non définie!")
client = MongoClient(mongo_uri)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== CONFIGURATION RESEND ====================
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
    print("✅ Resend configuré")
else:
    print("❌ RESEND_API_KEY manquante")

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

# ==================== UPDATE USER ====================
@user.route("/update/<user_id>", methods=["PUT", "OPTIONS"])
def update_user_by_id(user_id):
    if request.method == "OPTIONS":
        response = current_app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "https://helpful-llama-57b693.netlify.app")
        response.headers.add("Access-Control-Allow-Methods", "PUT, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token manquant"}), 401

    try:
        token = auth_header.split()[1]
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        current_user_id = payload.get('user_id')
        current_user_role = payload.get('role')

        if current_user_role not in ['admin', 'it_consultant'] and str(current_user_id) != user_id:
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

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== SUPPRESSION SON PROPRE COMPTE ====================
@user.route("/delete-me", methods=["DELETE", "OPTIONS"])
def delete_me():
    if request.method == "OPTIONS":
        response = current_app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "https://helpful-llama-57b693.netlify.app")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token manquant"}), 401

    try:
        token = auth_header.split()[1]
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        user_id = payload.get('user_id')

        result = users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count:
            return jsonify({"message": "Compte supprimé avec succès"}), 200
        return jsonify({"error": "Compte non trouvé"}), 404

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== DELETE USER (par admin) ====================
@user.route("/delete/<user_id>", methods=["DELETE", "OPTIONS"])
def delete_user_by_id(user_id):
    if request.method == "OPTIONS":
        response = current_app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "https://helpful-llama-57b693.netlify.app")
        response.headers.add("Access-Control-Allow-Methods", "DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Token manquant"}), 401

    try:
        token = auth_header.split()[1]
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
        current_user_id = payload.get('user_id')
        current_user_role = payload.get('role')

        if current_user_role not in ['admin', 'it_consultant']:
            return jsonify({"error": "Action non autorisée. Droits administrateur requis."}), 403

        if str(current_user_id) == user_id:
            return jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte"}), 400

        result = users_collection.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count:
            return jsonify({"message": "Utilisateur supprimé avec succès"}), 200
        return jsonify({"error": "Utilisateur non trouvé"}), 404

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expiré"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== FORGOT PASSWORD ====================
@user.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200

    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requis'}), 400

    user_doc = users_collection.find_one({"email": email})
    if not user_doc:
        return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

    token = generate_reset_token(email)
    reset_link = f"https://helpful-llama-57b693.netlify.app/reset-password?token={token}"

    if RESEND_API_KEY:
        try:
            resend.Emails.send({
                "from": "IT Support <onboarding@resend.dev>",
                "to": [email],
                "subject": "Réinitialisation de votre mot de passe",
                "html": f"<a href='{reset_link}'>Cliquez ici pour réinitialiser</a>"
            })
            print(f"✅ Email envoyé à {email}")
        except Exception as e:
            print(f"❌ Erreur Resend: {e}")
    else:
        print("❌ RESEND_API_KEY manquante, lien direct: {reset_link}")

    return jsonify({'reset_link': reset_link, 'token': token}), 200

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
    return jsonify({'error': 'Erreur lors de la mise à jour'}), 500s