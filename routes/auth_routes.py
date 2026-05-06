from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

auth = Blueprint("auth", __name__)

# ==================== CONNEXION MONGODB ====================
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI n'est pas définie dans les variables d'environnement!")

client = MongoClient(MONGO_URI)
db = client["pfe_db"]
users_collection = db["users"]

# ==================== ROUTES ====================

@auth.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        # Récupération des champs (supporte fullName ou username)
        username = data.get('username') or data.get('fullName') or data.get('name')
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'it_consultant')
        
        # Validation
        if not email:
            return jsonify({"error": "Email requis"}), 400
        if not password:
            return jsonify({"error": "Mot de passe requis"}), 400
        if not username:
            return jsonify({"error": "Nom d'utilisateur requis"}), 400
        
        # Vérifie si l'email existe déjà (PEU IMPORTE LE ROLE)
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({
                "error": "Cet email est déjà utilisé. Veuillez vous connecter."
            }), 400
        
        # Vérifie si le nom d'utilisateur existe déjà
        existing_username = users_collection.find_one({"username": username})
        if existing_username:
            return jsonify({
                "error": "Ce nom d'utilisateur est déjà pris."
            }), 400
        
        # Hash du mot de passe
        hashed_password = generate_password_hash(password).decode('utf-8')
        
        # Création de l'utilisateur
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
        
        # Génération du token JWT
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        # Préparation de la réponse utilisateur
        user_response = {
            "_id": user_id,
            "username": username,
            "email": email,
            "role": role,
            "created_at": user_data["created_at"]
        }
        
        return jsonify({
            "message": "Inscription réussie",
            "token": token,
            "user": user_response
        }), 201
        
    except Exception as e:
        print(f"Erreur inscription: {str(e)}")
        return jsonify({"error": f"Erreur lors de l'inscription: {str(e)}"}), 500

@auth.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données invalides"}), 400
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email et mot de passe requis"}), 400
        
        # Recherche de l'utilisateur par email
        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        
        # Vérification du mot de passe
        if not check_password_hash(user['password'], password):
            return jsonify({"error": "Email ou mot de passe incorrect"}), 401
        
        # Vérifie si le compte est actif
        if user.get('active') == False:
            return jsonify({"error": "Compte désactivé. Contactez l'administrateur."}), 401
        
        # Génération du token JWT
        token = jwt.encode({
            'user_id': str(user['_id']),
            'email': user['email'],
            'role': user.get('role', 'it_consultant'),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        # Préparation de la réponse
        user_response = {
            "_id": str(user['_id']),
            "username": user.get('username'),
            "email": user['email'],
            "role": user.get('role', 'it_consultant'),
            "created_at": user.get('created_at')
        }
        
        return jsonify({
            "message": "Connexion réussie",
            "token": token,
            "user": user_response
        }), 200
        
    except Exception as e:
        print(f"Erreur connexion: {str(e)}")
        return jsonify({"error": f"Erreur lors de la connexion: {str(e)}"}), 500

@auth.route("/me", methods=["GET"])
def get_me():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "Token manquant"}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return jsonify({"error": "Format du token invalide"}), 401
        
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
            
    except Exception as e:
        print(f"Erreur get_me: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route("/check-email", methods=["POST"])
def check_email():
    """Vérifie si un email est déjà utilisé (utile pour le frontend)"""
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