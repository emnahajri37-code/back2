from flask import Blueprint, request, jsonify, current_app
import os
from bson.objectid import ObjectId
from auth_middleware import token_required
import jwt
import datetime
from flask_bcrypt import generate_password_hash
from flask_mail import Message
from pymongo import MongoClient
import threading

user = Blueprint("user", __name__)

# ==================== CONNEXION MONGODB ====================
mongo_uri = os.environ.get('MONGO_URI')
if not mongo_uri:
    raise ValueError("❌ MONGO_URI n'est pas définie dans les variables d'environnement!")
print(f"✅ Connexion à MongoDB avec URI: {mongo_uri[:30]}...")
client = MongoClient(mongo_uri)
db = client["pfe_db"]
users_collection = db["users"]

# ===========================
# HELPER CORS PREFLIGHT
# ===========================
def _build_cors_preflight_response():
    """Construit la réponse pour la requête OPTIONS (preflight CORS)."""
    response = current_app.make_default_options_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# ===========================
# HELPER: GENERATE & VERIFY TOKEN
# ===========================
def generate_reset_token(email):
    """Génère un token JWT contenant l'email, valable 1 heure."""
    payload = {
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_reset_token(token):
    """Retourne l'email si le token est valide, sinon None."""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('email')
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def update_user_password(email, hashed_password):
    """Met à jour le mot de passe dans MongoDB."""
    result = users_collection.update_one(
        {'email': email},
        {'$set': {'password': hashed_password}}
    )
    return result.modified_count > 0

# ===========================
# CRUD UTILISATEURS
# ===========================

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

# ===========================
# FORGOT PASSWORD
# ===========================
@user.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'error': 'Email requis'}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({'message': 'Si cet email est enregistré, vous recevrez un lien.'}), 200

    token = generate_reset_token(email)
    base_url = current_app.config.get('BASE_URL', 'http://localhost:3000')
    reset_link = f"{base_url}/reset-password?token={token}"

    # ✅ Envoyer l'email dans un thread séparé (non-bloquant)
    def send_email():
        with current_app.app_context():
            try:
                msg = Message(
                    subject="Réinitialisation de votre mot de passe",
                    recipients=[email],
                    body=f"Bonjour,\n\nCliquez sur ce lien :\n{reset_link}\n\nExpire dans 1 heure."
                )
                mail = current_app.extensions.get('mail')
                if mail:
                    mail.send(msg)
                    print("✅ Email envoyé")
            except Exception as e:
                print(f"❌ Erreur email: {e}")

    thread = threading.Thread(target=send_email)
    thread.start()

    # ✅ Répondre immédiatement sans attendre l'email
    return jsonify({'message': 'Un email de réinitialisation a été envoyé.'}), 200
# ===========================
# RESET PASSWORD
# ===========================
@user.route("/reset-password", methods=["OPTIONS", "POST"])
def reset_password():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')

    if not token or not new_password or not confirm_password:
        return jsonify({'error': 'Token, nouveau mot de passe et confirmation requis'}), 400

    if new_password != confirm_password:
        return jsonify({'error': 'Les mots de passe ne correspondent pas'}), 400

    email = verify_reset_token(token)
    if not email:
        return jsonify({'error': 'Le lien de réinitialisation est invalide ou a expiré.'}), 400

    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404

    hashed = generate_password_hash(new_password).decode('utf-8')
    if update_user_password(email, hashed):
        return jsonify({'message': 'Votre mot de passe a été réinitialisé avec succès.'}), 200
    else:
        return jsonify({'error': 'Erreur lors de la mise à jour'}), 500

# ===========================
# ROUTE DE DEBUG
# ===========================
@user.route("/debug-token", methods=["OPTIONS", "POST"])
def debug_token():
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()
    
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