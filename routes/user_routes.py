from flask import Blueprint, request, jsonify
from models.user_model import *

user = Blueprint("user", __name__)

# ✅ GET ALL USERS
@user.route("/users", methods=["GET"])
def get_users():
    return jsonify(get_all_users())


# ✅ GET ONE USER
@user.route("/users/<id>", methods=["GET"])
def get_user_route(id):
    user_data = get_user_by_id(id)

    if not user_data:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user_data)


# ✅ UPDATE USER
@user.route("/users/<id>", methods=["PUT"])
def update_user_route(id):
    data = request.json
    update_user(id, data)

    return jsonify({"message": "User updated"})


# ✅ DELETE USER
@user.route("/users/<id>", methods=["DELETE"])
def delete_user_route(id):
    delete_user(id)
    return jsonify({"message": "User deleted"})