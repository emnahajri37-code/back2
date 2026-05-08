from flask import Blueprint, request, jsonify, current_app
import os
from bson.objectid import ObjectId
from auth_middleware import token_required
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
import resend

user = Blueprint("user", __name__)

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

# ==================== HELPER CORS ====================
def _cors_response(response):
    response.headers.add("Access-Control-Allow-Origin", "https://sparkling-wisp-363896.netlify.app")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return response

# ==================== UPDATE USER ====================
@user.route("/<user_id>", methods=["PUT", "OPTIONS"])
@token_required
def update_user(current_user, user_id):
    if request.method == "OPTIONS":
        return _cors_response(current_app.make_default_options_response()), 200
    
    # Vérification des droits
    if current_user.get('role') not in ['admin', 'it_consultant'] and str(current_user.get('_id')) != user_id:
        return _cors_response(jsonify({"error": "Action non autorisée"})), 403
    
    data = request.json
    if not data:
        return _cors_response(jsonify({"error": "Données manquantes"})), 400
    
    # Champs autorisés
    allowed_fields = ["username", "name", "role"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    
    if "password" in data and data["password"]:
        update_data["password"] = generate_password_hash(data["password"]).decode('utf-8')
    
    if not update_data:
        return _cors_response(jsonify({"error": "Aucun champ valide"})), 400
    
    result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    
    if result.matched_count == 0:
        return _cors_response(jsonify({"error": "Utilisateur non trouvé"})), 404
    
    user_updated = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    user_updated["_id"] = str(user_updated["_id"])
    return _cors_response(jsonify({"message": "Utilisateur mis à jour", "user": user_updated})), 200

# ==================== DELETE USER ====================
@user.route("/<user_id>", methods=["DELETE", "OPTIONS"])
@token_required
def delete_user(current_user, user_id):
    if request.method == "OPTIONS":
        return _cors_response(current_app.make_default_options_response()), 200
    
    # Vérification des droits (admin ou IT consultant uniquement)
    if current_user.get('role') not in ['admin', 'it_consultant']:
        return _cors_response(jsonify({"error": "Action non autorisée. Droits administrateur requis."})), 403
    
    # Empêche la suppression de son propre compte
    if str(current_user.get('_id')) == user_id:
        return _cors_response(jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte"})), 400
    
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    
    if result.deleted_count:
        return _cors_response(jsonify({"message": "Utilisateur supprimé avec succès"})), 200
    
    return _cors_response(jsonify({"error": "Utilisateur non trouvé"})), 404

# ==================== FORGOT PASSWORD ====================
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
    except:
        return None

def update_user_password(email, hashed_password):
    result = users_collection.update_one({'email': email}, {'$set': {'password': hashed_password}})
    return result.modified_count > 0

@user.route("/forgot-password", methods=["POST", "OPTIONS"])
def forgot_password():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'error': 'Email requis'}), 400
    user = users_collection.find_one({"email": email})
    if not user:
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
                "html": f"<a href='{reset_link}'>Cliquez ici pour réinitialiser</a>"
            })
            print(f"✅ Email envoyé à {email}")
        else:
            print(f"🔑 Token pour {email}: {reset_link}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

@user.route("/reset-password", methods=["POST", "OPTIONS"])
def reset_password():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    if not token or not new_password or not confirm_password:
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400
    email = verify_reset_token(token)
    if not email:
        return jsonify({'error': 'Lien invalide ou expiré'}), 400
    hashed = generate_password_hash(new_password).decode('utf-8')
    if update_user_password(email, hashed):
        return jsonify({'message': 'Mot de passe réinitialisé avec succès'}), 200
    return jsonify({'error': 'Erreur lors de la mise à jour'}), 500
@user.route("/test-delete/<user_id>", methods=["DELETE"])
def test_delete(user_id):
    return jsonify({"message": f"DELETE test for {user_id}"}), 200