import os
from flask import Flask, request
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail

from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_super_cle_secrete_pour_les_tokens_12345!')
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:3000')

# Configuration email
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'emnasellami18@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'uiobnsjfeqcvetou')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'ticketsystempfe@gmail.com')

# Initialisation
bcrypt = Bcrypt(app)
mail = Mail(app)
app.extensions['mail'] = mail

# ==================== CORS COMPLET ====================
CORS(app, 
     origins=["https://sparkling-wisp-363896.netlify.app", "http://localhost:3000", "*"],
     supports_credentials=True, 
     allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Middleware CORS manuel pour toutes les routes
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://sparkling-wisp-363896.netlify.app')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Route OPTIONS globale pour gérer les preflight requests
@app.route('/<path:path>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def handle_options(path=None):
    response = app.make_default_options_response()
    response.headers.add('Access-Control-Allow-Origin', 'https://sparkling-wisp-363896.netlify.app')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Route de test
@app.route("/")
def home():
    return "Bienvenue sur le backend"

# Blueprints
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)