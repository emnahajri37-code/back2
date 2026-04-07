from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import joblib

# Routes existantes
from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

# ==========================
# APP CONFIG
# ==========================

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

# ==========================
# LOAD MODEL (pour prédire le type de ticket)
# ==========================

model = joblib.load("model_pipeline.pkl")   # modèle existant (type de ticket)

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

    text = data["text"]

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

    print("TEXT:", text)
    print("PREDICTION:", prediction)

    return jsonify({"prediction": prediction})

# ==========================
# RUN SERVER
# ==========================

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)