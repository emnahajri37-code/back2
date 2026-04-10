from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import os

from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ma_super_cle_secrete_pour_les_tokens_12345!'
app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5000')

# Configuration email (Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = "emnasellami18@gmail.com"
app.config['MAIL_PASSWORD'] = "kdhvvvtxpmoygkrg"
app.config['MAIL_DEFAULT_SENDER'] = "emnasellami18@gmail.com"

bcrypt = Bcrypt(app)
mail = Mail(app)
app.extensions['mail'] = mail

# CORS – autorise les requêtes depuis le frontend React
CORS(app, origins=["http://localhost:3000"], supports_credentials=True, allow_headers=["Content-Type", "Authorization"])

# Enregistrement des blueprints
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

@app.route("/")
def home():
    return "Bienvenue sur le backend"

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)