from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from pymongo import MongoClient
import os
from auth_middleware import token_required

auth = Blueprint("auth", __name__)

client = MongoClient(os.environ.get('MONGO_URI'))
db = client["pfe_db"]
users_collection = db["users"]

@auth.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'it_consultant')
    
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400
    
    existing_user = users_collection.find_one({"$or": [{"email": email}, {"username": username}]})
    if existing_user:
        return jsonify({"error": "Utilisateur déjà existant"}), 400
    
    hashed_password = generate_password_hash(password).decode('utf-8')
    
    user_data = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "role": role,
        "created_at": datetime.datetime.utcnow()
    }
    
    result = users_collection.insert_one(user_data)
    user_data["_id"] = str(result.inserted_id)
    del user_data["password"]
    
    token = jwt.encode({
        'user_id': str(result.inserted_id),
        'email': email,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        "message": "Utilisateur créé avec succès",
        "token": token,
        "user": user_data
    }), 201

@auth.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400
    
    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    
    if not check_password_hash(user['password'], password):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    
    token = jwt.encode({
        'user_id': str(user['_id']),
        'email': user['email'],
        'role': user.get('role', 'it_consultant'),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    user_data = {
        "_id": str(user['_id']),
        "username": user.get('username'),
        "email": user['email'],
        "role": user.get('role', 'it_consultant')
    }
    
    return jsonify({
        "message": "Connexion réussie",
        "token": token,
        "user": user_data
    }), 200

@auth.route("/me", methods=["GET"])
@token_required
def get_me(current_user):
    user = users_collection.find_one({"_id": current_user["_id"]}, {"password": 0})
    if not user:
        return jsonify({"error": "Utilisateur non trouvé"}), 404
    user["_id"] = str(user["_id"])
    return jsonify(user), 200