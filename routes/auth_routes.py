from flask import Blueprint, request, jsonify
from models.user_db import create_user, find_user_by_email, check_password
import jwt
import datetime
import re

auth = Blueprint("auth", __name__)
SECRET_KEY = "secret123"

@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")

    # Vérification champs obligatoires
    if not email or not password or not name:
        return jsonify({"error": "Email, password et name requis"}), 400

    # Vérifier si email existe déjà
    if find_user_by_email(email):
        return jsonify({"error": "Email déjà utilisé"}), 400

    # ✅ Validation du mot de passe sécurisé
    if len(password) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400

    if not re.search(r"[A-Z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre majuscule"}), 400

    if not re.search(r"[a-z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre minuscule"}), 400

    if not re.search(r"[0-9]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins un chiffre"}), 400

    # Hash password
    from models.user_db import bcrypt
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")

    # Création utilisateur
    user = create_user(email, hashed, name)
    user.pop("password", None)

    return jsonify({
        "message": "Utilisateur créé avec succès",
        "user": user
    }), 201


@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # Vérification champs
    if not email or not password:
        return jsonify({"error": "Email et password requis"}), 400

    user = find_user_by_email(email)
    if not user:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    password_check = check_password(password, user.get("password", ""))
    if not password_check:
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    # Génération token JWT
    token = jwt.encode({
        "user_id": str(user["_id"]),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    user.pop("password", None)

    return jsonify({
        "message": "Connexion réussie",
        "token": token,
        "user": user
    }), 200