@auth.route("/google", methods=["POST"])
def google_login():
    try:
        data = request.get_json()
        id_token_credential = data.get('id_token') or data.get('credential')
        
        if not id_token_credential:
            return jsonify({"error": "Token Google manquant"}), 400
        
        # Vérification du token Google
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        
        GOOGLE_CLIENT_ID = "84499611206-pquink4aps0ked49ngi5t3rqk5p6ho6v.apps.googleusercontent.com"
        try:
            info = id_token.verify_oauth2_token(id_token_credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        except Exception as e:
            return jsonify({"error": "Token Google invalide"}), 400
        
        email = info.get('email')
        name = info.get('name')
        role = data.get('role', 'developer')
        
        if not email:
            return jsonify({"error": "Email non fourni par Google"}), 400
        
        # 🔒 VÉRIFICATION EMAIL UNIQUE
        existing_user = users_collection.find_one({"email": email})
        
        if existing_user:
            # ⚠️ L'email existe déjà → on ne crée PAS de nouveau compte
            # On connecte l'utilisateur existant si son rôle correspond
            if existing_user.get('role') != role:
                return jsonify({
                    "error": f"Cet email est déjà utilisé pour un compte {existing_user.get('role')}. Veuillez vous connecter avec celui-ci."
                }), 400
            
            # Connexion existant
            user_id = str(existing_user['_id'])
            user_role = existing_user.get('role')
            user_username = existing_user.get('username', name)
            
            # Met à jour google_id si manquant
            if not existing_user.get('google_id'):
                users_collection.update_one({"email": email}, {"$set": {"google_id": info.get('sub')}})
        
        else:
            # ➕ Création nouveau compte UNIQUEMENT si email inconnu
            user_data = {
                "username": name,
                "email": email,
                "google_id": info.get('sub'),
                "role": role,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "email_verified": True,
                "active": True
            }
            result = users_collection.insert_one(user_data)
            user_id = str(result.inserted_id)
            user_role = role
            user_username = name
        
        # Génération du token JWT
        token = jwt.encode({
            'user_id': user_id,
            'email': email,
            'role': user_role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            "success": True,
            "message": "Connexion Google réussie",
            "token": token,
            "user": {
                "_id": user_id,
                "username": user_username,
                "email": email,
                "role": user_role
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Google auth error: {str(e)}")
        return jsonify({"success": False, "error": "Erreur d'authentification Google"}), 500