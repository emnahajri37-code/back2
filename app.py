import os
from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from pymongo import MongoClient

from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ma_super_cle_secrete_12345!')
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:3000')
app.config['FRONTEND_URL'] = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Configuration MongoDB
app.config['MONGO_URI'] = os.environ.get('MONGODB_URI') or os.environ.get('MONGO_URI')
if not app.config['MONGO_URI']:
    raise ValueError("❌ MONGODB_URI ou MONGO_URI non définie dans les variables d'environnement!")

# Configuration email — tout depuis les variables d'env
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')

# Validation des variables email
if not app.config['MAIL_USERNAME']:
    print("⚠️  Attention: MAIL_USERNAME non défini - L'envoi d'email ne fonctionnera pas")
if not app.config['MAIL_PASSWORD']:
    print("⚠️  Attention: MAIL_PASSWORD non défini - L'envoi d'email ne fonctionnera pas")

# ==================== DIAGNOSTIC AU DÉMARRAGE ====================
print("\n" + "="*50)
print("🔍 DIAGNOSTIC DE CONFIGURATION - BACKEND")
print("="*50)

print("\n📧 CONFIGURATION EMAIL:")
print(f"  - MAIL_USERNAME: {app.config['MAIL_USERNAME']}")
print(f"  - MAIL_PASSWORD: {'✅ DÉFINI' if app.config['MAIL_PASSWORD'] else '❌ NON DÉFINI'}")
print(f"  - MAIL_DEFAULT_SENDER: {app.config['MAIL_DEFAULT_SENDER']}")
print(f"  - MAIL_SERVER: {app.config['MAIL_SERVER']}")
print(f"  - MAIL_PORT: {app.config['MAIL_PORT']}")

print("\n🍃 CONFIGURATION MONGODB:")
mongo_uri = app.config['MONGO_URI']
if mongo_uri:
    if '@' in mongo_uri:
        parts = mongo_uri.split('@')
        safe_uri = f"{parts[0][:30]}...@{parts[1][:20]}..."
        print(f"  - MONGO_URI: ✅ {safe_uri}")
    else:
        print(f"  - MONGO_URI: ❌ URI CORROMPUE (manque le @)")
else:
    print(f"  - MONGO_URI: ❌ NON DÉFINIE")

print("\n🔗 URLs:")
print(f"  - BASE_URL: {app.config['BASE_URL']}")
print(f"  - FRONTEND_URL: {app.config['FRONTEND_URL']}")

print("\n🔐 SÉCURITÉ:")
print(f"  - SECRET_KEY: {'✅ DÉFINIE' if app.config['SECRET_KEY'] != 'ma_super_cle_secrete_12345!' else '⚠️  UTILISE VALEUR PAR DÉFAUT'}")
print("="*50 + "\n")

# ==================== INITIALISATION MONGODB ====================
try:
    mongo_client = MongoClient(app.config['MONGO_URI'], serverSelectionTimeoutMS=5000)
    mongo_client.admin.command('ping')
    print("✅ Connexion à MongoDB Atlas réussie!")
    app.db = mongo_client.get_database()
except Exception as e:
    print(f"❌ Erreur de connexion MongoDB: {e}")
    print("⚠️  L'application peut continuer mais les opérations base de données échoueront")
    app.db = None

# ==================== INITIALISATION ====================
bcrypt = Bcrypt(app)

# Initialisation de Mail avec gestion d'erreur
try:
    mail = Mail(app)
    app.extensions['mail'] = mail
    print("✅ Service email initialisé avec succès")
except Exception as e:
    print(f"❌ Erreur d'initialisation email: {e}")
    app.extensions['mail'] = None

# ==================== CORS ====================
CORS(app,
     origins=[
         "http://localhost:3000",
         "http://localhost:5000",
         "https://ticket-app-2026.netlify.app",
         "https://back2-ys67.onrender.com"
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# ==================== ROUTES ====================
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

@app.route("/")
def home():
    return {
        "message": "Bienvenue sur le backend IT Support System",
        "status": "online",
        "mongodb": "connected" if app.db else "disconnected",
        "email": "configured" if app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD'] else "missing"
    }

@app.route("/health")
def health():
    """Endpoint de santé pour Render"""
    return {"status": "healthy", "timestamp": os.popen('date').read().strip()}, 200

# ==================== GESTION DES ERREURS ====================
@app.errorhandler(404)
def not_found(e):
    return {"error": "Route non trouvée"}, 404

@app.errorhandler(500)
def internal_error(e):
    return {"error": "Erreur interne du serveur"}, 500

# ==================== DEMARRAGE ====================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Démarrage du serveur sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)