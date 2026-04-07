from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_mail import Mail
import joblib
import os

# Routes existantes
from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

# ==========================
# APP CONFIG
# ==========================
app = Flask(__name__)

# ⭐ Clé secrète FIXE (pour la cohérence des tokens JWT)
app.config['SECRET_KEY'] = 'ma_super_cle_secrete_pour_les_tokens_12345!'
# En production, utilisez une variable d'environnement :
# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-key')

app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5000')

# Configuration SMTP (avec MailHog en développement)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = "emnasellami18@gmail.com"
app.config['MAIL_PASSWORD'] = "kdhvvvtxpmoygkrg"
app.config['MAIL_DEFAULT_SENDER'] = "emnasellami18@gmail.com"


# Initialisation des extensions
bcrypt = Bcrypt(app)
CORS(app)
mail = Mail(app)

# Rendre l'instance mail accessible dans les blueprints
app.extensions['mail'] = mail

# ==========================
# LOAD MODEL (prédiction type ticket)
# ==========================
model = joblib.load("model_pipeline.pkl")

# ==========================
# PRIORITY RULES (heuristique)
# ==========================
def get_priority_from_text(text: str) -> str:
    text_lower = text.lower()
    high_keywords = [
        "urgent", "asap", "critical", "blocking", "emergency",
        "down", "outage", "not working", "broken", "crash",
        "data loss", "security breach", "immediately"
    ]
    low_keywords = [
        "low priority", "not urgent", "when possible", "suggestion",
        "minor issue", "cosmetic", "nice to have", "eventually"
    ]
    if any(kw in text_lower for kw in high_keywords):
        return "high"
    elif any(kw in text_lower for kw in low_keywords):
        return "low"
    else:
        return "medium"

# ==========================
# REGISTER BLUEPRINTS
# ==========================
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

# ==========================
# HOME ROUTE
# ==========================
@app.route("/")
def home():
    return "Bienvenue sur le backend"

# ==========================
# PREDICT ROUTE (type de ticket)
# ==========================
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
    text = data["text"]
<<<<<<< HEAD

    text = data["text"]

=======
>>>>>>> 000cf86cf891a3f681d6278826ccde970c4baa65
    prediction = model.predict([text])[0]
    return jsonify({"prediction": prediction})

# ==========================
# PREDICT PRIORITY ROUTE (heuristique)
# ==========================
@app.route("/predict_priority", methods=["POST"])
def predict_priority():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
    text = data["text"]
    priority = get_priority_from_text(text)
    return jsonify({"priority": priority})
<<<<<<< HEAD

    print("TEXT:", text)
    print("PREDICTION:", prediction)

    return jsonify({"prediction": prediction})
=======
>>>>>>> 000cf86cf891a3f681d6278826ccde970c4baa65

# ==========================
# RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)