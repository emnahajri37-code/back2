from flask import Flask
from flask_cors import CORS

from routes.auth_routes import auth
from routes.user_routes import user
from routes.ticket_routes import ticket

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth, url_prefix="/api")
app.register_blueprint(user, url_prefix="/api")
app.register_blueprint(ticket, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=False)