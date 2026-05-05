from flask import Blueprint, request, jsonify, current_app
from models.user_db import (
    create_user, find_user_by_email, check_password, generate_verification_code,
    verify_user_code, find_user_by_email_for_google, create_google_user
)
import jwt
import datetime
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from config.db import GOOGLE_CLIENT_ID
from flask_bcrypt import Bcrypt
from flask_mail import Message
from bson.objectid import ObjectId
import os
auth = Blueprint("auth", __name__)
SECRET_KEY = "secret123"
bcrypt = Bcrypt()

@auth.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    role = data.get("role", "it_consultant")

    if not email or not password or not name:
        return jsonify({"error": "Email, password et name requis"}), 400

    if find_user_by_email(email):
        return jsonify({"error": "Email déjà utilisé"}), 400

    # Validation mot de passe
    if len(password) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre majuscule"}), 400
    if not re.search(r"[a-z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre minuscule"}), 400
    if not re.search(r"[0-9]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins un chiffre"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    code = generate_verification_code()
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    user = create_user(email, hashed, name, role, code, expiry)
    user.pop("password", None)
    user.pop("verification_code", None)
    user.pop("verification_code_expiry", None)

    # Envoi de l'email avec le code
    base_url = current_app.config.get('BASE_URL', 'http://localhost:3000')
    try:
        msg = Message(
            subject="Votre code de vérification",
            recipients=[email],
            body=f"Bonjour {name},\n\nMerci de vous être inscrit sur IT Support System.\n\nVotre code de vérification est : {code}\n\nCe code expire dans 15 minutes.\n\nRendez-vous sur {base_url}/verify-email pour le valider.\n\nSi vous n'êtes pas à l'origine, ignorez cet email."
        )
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return jsonify({"error": "Inscription réussie mais impossible d'envoyer l'email de vérification."}), 201

    return jsonify({
        "message": "Inscription réussie. Un code de vérification vous a été envoyé par email.",
        "user": user
    }), 201

@auth.route("/verify-email", methods=["POST"])
def verify_email():
    data = request.get_json()
    email = data.get("email")
    code = data.get("code")
    if not email or not code:
        return jsonify({"error": "Email et code requis"}), 400

    if verify_user_code(email, code):
        return jsonify({"message": "Email vérifié avec succès. Vous pouvez maintenant vous connecter."}), 200
    else:
        return jsonify({"error": "Code invalide ou expiré"}), 400

@auth.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    role_requested = data.get("role")  # 🔥 IMPORTANT

    if not email or not password:
        return jsonify({"error": "Email et password requis"}), 400

    user = find_user_by_email(email)

    if not user or not check_password(password, user.get("password", "")):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    # 🔥 BLOQUER SI ROLE DIFFERENT
    if role_requested and user.get("role") != role_requested:
        return jsonify({
            "error": f"Ce compte est un compte '{user.get('role')}'. Utilisez la bonne page de connexion."
        }), 403

    if not user.get("email_verified", False):
        return jsonify({
            "error": "Veuillez vérifier votre email avec le code reçu avant de vous connecter."
        }), 401

    token = jwt.encode({
        "user_id": str(user["_id"]),
        "role": user.get("role", "it_consultant"),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    user.pop("password", None)

    return jsonify({
        "message": "Connexion réussie",
        "token": token,
        "user": user
    }), 200

# ========== GOOGLE AUTH ==========
@auth.route("/google", methods=["POST"])
def google_login():
    try:
        data = request.get_json()
        id_token_str = data.get('id_token')
        role_requested = data.get('role', 'it_consultant')

        if not id_token_str:
            return jsonify({"error": "Token manquant"}), 400

        info = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        if info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return jsonify({"error": "Token invalide"}), 401

        google_id = info.get('sub')
        email = info.get('email')
        name = info.get('name')
        picture = info.get('picture')
        print(f"🔍 Tentative de connexion Google: {email} (rôle demandé: {role_requested})")

        user = find_user_by_email_for_google(email)

        if user:
            user_role = user.get('role', 'it_consultant')
            if user_role != role_requested:
                return jsonify({
                    "error": "Cet email est déjà utilisé avec un compte {user_role}. Veuillez utiliser l'autre page de connexion."
                }), 409
            if not user.get('google_id'):
                link_google_account(email, google_id)
                user['google_id'] = google_id
        else:
            print(f"✨ Création d'un nouvel utilisateur Google: {email} avec rôle {role_requested}")
            user = create_google_user(google_id, email, name, picture, role_requested)

        token = jwt.encode({
            "user_id": user['_id'],
            "role": user.get('role', role_requested),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm="HS256")

        user_for_response = {
            "id": user['_id'],
            "email": user['email'],
            "name": user.get('name'),
            "picture": user.get('picture', ''),
            "role": user.get('role', role_requested)
        }

        return jsonify({
            "success": True,
            "message": "Connexion Google réussie",
            "token": token,
            "user": user_for_response
        }), 200

    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500

@auth.route("/google/config", methods=["GET"])
def google_config():
    return jsonify({"client_id": GOOGLE_CLIENT_ID})

@auth.route("/google/callback", methods=["GET"])
def google_callback():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Connexion Google - Token reçu</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .token { background: #f0f0f0; padding: 10px; word-break: break-all; font-family: monospace; }
        button { background: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; margin-top: 20px; }
        .success { color: green; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>🔄 Traitement de la connexion Google...</h1>
    <div id="status">Extraction du token en cours...</div>
    <script>
        const hash = window.location.hash.substring(1);
        const params = new URLSearchParams(hash);
        const id_token = params.get('id_token');
        if (id_token) {
            document.getElementById('status').innerHTML = `
                <p class="success">✅ Token reçu avec succès !</p>
                <p><strong>Token :</strong></p>
                <div class="token">${id_token}</div>
                <p>📋 Copiez ce token et testez-le dans Postman :</p>
                <p><code>POST http://localhost:5000/auth/google</code></p>
                <p><code>Content-Type: application/json</code></p>
                <p><code>{"id_token": "LE_TOKEN_CI_DESSUS"}</code></p>
                <button onclick="copyToken()">📋 Copier le token</button>
            `;
            fetch('https://back2-ys67.onrender.com/auth/google', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id_token: id_token})
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').innerHTML += `
                        <p class="success">✅ Connexion réussie !</p>
                        <pre>${JSON.stringify(data, null, 2)}</pre>
                    `;
                } else {
                    document.getElementById('status').innerHTML += `
                        <p class="error">❌ Erreur: ${data.error}</p>
                    `;
                }
            })
            .catch(err => {
                document.getElementById('status').innerHTML += `
                    <p class="error">❌ Erreur lors de l'envoi: ${err.message}</p>
                `;
            });
        } else {
            document.getElementById('status').innerHTML = `
                <p class="error">❌ Aucun token trouvé dans l'URL</p>
                <p>Assurez-vous de vous connecter correctement.</p>
            `;
        }
        function copyToken() {
            const token = document.querySelector('.token').textContent;
            navigator.clipboard.writeText(token);
            alert('Token copié dans le presse-papier !');
        }
    </script>
</body>
</html>"""