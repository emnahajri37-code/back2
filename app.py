import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_super_cle_secrete_pour_les_tokens_12345!')
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')

# ==================== CORS ====================
CORS(app, 
     origins=["https://sparkling-wisp-363896.netlify.app"],
     allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
     supports_credentials=True)

# ✅ CRITIQUE : intercepte tous les preflight OPTIONS avant @token_required
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return jsonify({"ok": True}), 200

# ==================== ROUTES ====================
@app.route("/")
def home():
    return "Bienvenue sur le backend"

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)