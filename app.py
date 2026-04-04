from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS

# Routes
from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)
bcrypt = Bcrypt(app)
CORS(app)

# Enregistrer les routes
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(user, url_prefix="/user")
app.register_blueprint(ticket, url_prefix="/tickets")

@app.route("/")
def home():
    return "Bienvenue sur le backend"

if __name__ == "__main__":
    app.run(debug=True, port=5000)