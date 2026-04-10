from flask import Blueprint, request, jsonify
from models.user_db import create_user, find_user_by_email, check_password
import jwt
import datetime
import re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from config.db import GOOGLE_CLIENT_ID
from models import user_db as user_model
from flask_bcrypt import Bcrypt

auth = Blueprint("auth", __name__)
SECRET_KEY = "secret123"
bcrypt = Bcrypt()  # utilisé uniquement pour générer le hash lors de l'inscription

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

    if len(password) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
    if not re.search(r"[A-Z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre majuscule"}), 400
    if not re.search(r"[a-z]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins une lettre minuscule"}), 400
    if not re.search(r"[0-9]", password):
        return jsonify({"error": "Le mot de passe doit contenir au moins un chiffre"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = create_user(email, hashed, name, role)
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

    if not email or not password:
        return jsonify({"error": "Email et password requis"}), 400

    user = find_user_by_email(email)
    if not user or not check_password(password, user.get("password", "")):
        return jsonify({"error": "Email ou mot de passe incorrect"}), 401

    token = jwt.encode({
        "user_id": user["_id"],
        "role": user.get("role", "it_consultant"),  # ← le rôle est bien présent
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    user.pop("password", None)
    return jsonify({
        "message": "Connexion réussie",
        "token": token,
        "user": user          # ← user contient le champ "role"
    }), 200
# ========== GOOGLE AUTH (inchangé) ==========
@auth.route("/google", methods=["POST"])
def google_login():
    try:
        data = request.get_json()
        id_token_str = data.get('id_token')
        if not id_token_str:
            return jsonify({"error": "Token manquant"}), 400
        try:
            info = id_token.verify_oauth2_token(
                id_token_str, 
                google_requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            if info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                return jsonify({"error": "Token invalide"}), 401
        except ValueError as e:
            return jsonify({"error": f"Token invalide: {str(e)}"}), 401
        
        google_id = info.get('sub')
        email = info.get('email')
        name = info.get('name')
        picture = info.get('picture')
        print(f"🔍 Tentative de connexion Google: {email}")
        
        user = user_model.find_user_by_google_id(google_id)
        if not user:
            user = user_model.find_user_by_email_for_google(email)
            if user:
                print(f"🔗 Liaison du compte Google avec l'utilisateur existant: {email}")
                user_model.link_google_account(email, google_id)
                user['google_id'] = google_id
            else:
                print(f"✨ Création d'un nouvel utilisateur Google: {email}")
                user = user_model.create_google_user(google_id, email, name, picture)
        
        token = jwt.encode({
            "user_id": user['_id'],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm="HS256")
        
        return jsonify({
            "success": True,
            "message": "Connexion Google réussie",
            "token": token,
            "user": {
                "id": user['_id'],
                "email": user['email'],
                "name": user.get('name'),
                "picture": user.get('picture', '')
            }
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
            fetch('http://localhost:5000/auth/google', {
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