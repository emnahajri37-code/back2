@user.route("/<user_id>", methods=["GET", "PUT", "DELETE", "OPTIONS"])
@token_required
def user_by_id(current_user, user_id):
    if request.method == "OPTIONS":
        response = current_app.make_default_options_response()
        response.headers.add("Access-Control-Allow-Origin", "https://sparkling-wisp-363896.netlify.app")
        response.headers.add("Access-Control-Allow-Methods", "GET, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        return response, 200

    if request.method == "GET":
        try:
            user_data = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
            if not user_data:
                return jsonify({"error": "Utilisateur non trouvé"}), 404
            user_data["_id"] = str(user_data["_id"])
            return jsonify(user_data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "PUT":
        try:
            if current_user.get('role') not in ['admin', 'it_consultant'] and str(current_user.get('_id')) != user_id:
                return jsonify({"error": "Action non autorisée"}), 403

            data = request.json
            if not data:
                return jsonify({"error": "Données manquantes"}), 400

            allowed_fields = ["username", "name", "email", "phone", "location"]
            update_data = {k: v for k, v in data.items() if k in allowed_fields if v is not None}

            if "password" in data and data["password"]:
                if len(data["password"]) < 6:
                    return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
                update_data["password"] = generate_password_hash(data["password"]).decode('utf-8')

            if not update_data:
                return jsonify({"error": "Aucun champ valide à mettre à jour"}), 400

            result = users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            if result.matched_count == 0:
                return jsonify({"error": "Utilisateur non trouvé"}), 404

            user_updated = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
            if user_updated:
                user_updated["_id"] = str(user_updated["_id"])
            return jsonify({"message": "Utilisateur mis à jour", "user": user_updated}), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == "DELETE":
        try:
            if current_user.get('role') not in ['admin', 'it_consultant']:
                return jsonify({"error": "Action non autorisée. Droits administrateur requis."}), 403

            if str(current_user.get('_id')) == user_id:
                return jsonify({"error": "Vous ne pouvez pas supprimer votre propre compte"}), 400

            result = users_collection.delete_one({"_id": ObjectId(user_id)})
            if result.deleted_count:
                return jsonify({"message": "Utilisateur supprimé avec succès"}), 200
            return jsonify({"error": "Utilisateur non trouvé"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500