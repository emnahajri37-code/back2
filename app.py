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
# LOAD MODEL
# ==========================

model = joblib.load("model_pipeline.pkl")

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
# PREDICT ROUTE
# ==========================

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    text = data["text"]

    prediction = model.predict([text])[0]

    print("TEXT:", text)
    print("PREDICTION:", prediction)

    return jsonify({"prediction": prediction})

# ==========================
# RUN SERVER
# ==========================

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)