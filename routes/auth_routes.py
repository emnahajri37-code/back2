from flask import Blueprint, request, jsonify
from models.user_db import create_user, find_user_by_email, check_password
import jwt
import datetime

auth = Blueprint("auth", __name__)
SECRET_KEY = "secret123"

@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    if not email or not password or not name:
        return jsonify({"error": "Email, password et name requis"}), 400
    if find_user_by_email(email):
        return jsonify({"error": "Email déjà utilisé"}), 400
    # Utilise l'instance bcrypt de user_db via une fonction utilitaire
    from models.user_db import bcrypt
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = create_user(email, hashed, name)
    user.pop("password", None)
    return jsonify({"message": "Utilisateur créé", "user": user})

@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"error": "Email et password requis"}), 400
    user = find_user_by_email(email)
    if not user:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    password_check = check_password(password, user.get("password", ""))
    if not password_check:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401
    token = jwt.encode({
        "user_id": str(user["_id"]),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")
    user.pop("password", None)
    return jsonify({"message": "Connexion réussie", "token": token, "user": user})