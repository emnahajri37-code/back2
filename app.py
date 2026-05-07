import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_super_cle_secrete_pour_les_tokens_12345!')
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'https://sparkling-wisp-363896.netlify.app')

# Configuration email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp-relay.brevo.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
app.config['MAIL_TIMEOUT'] = 10

# Initialisation
bcrypt = Bcrypt(app)
mail = Mail(app)
app.extensions['mail'] = mail

# ==================== CORS CORRIGÉ ====================
# Configuration CORS complète
CORS(app, 
     origins=[
         "https://sparkling-wisp-363896.netlify.app",
         "http://localhost:3000",
         "http://localhost:5173"
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
     expose_headers=["Content-Type", "Authorization"])

# Middleware CORS pour garantir les headers après chaque requête
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://sparkling-wisp-363896.netlify.app')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept, X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Middleware pour gérer les requêtes OPTIONS
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "https://sparkling-wisp-363896.netlify.app")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization, Accept")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response

# ==================== ROUTES ====================
@app.route("/")
def home():
    return "Bienvenue sur le backend"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend is running"}), 200

app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

# ==================== DEMARRAGE ====================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)