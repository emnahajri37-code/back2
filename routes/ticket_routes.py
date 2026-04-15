from flask import Blueprint, request, jsonify
import joblib
import re
from models.ticket_db import create_ticket, get_tickets_by_user, get_ticket_by_id, update_ticket, delete_ticket, get_all_tickets
from auth_middleware import token_required
import datetime

ticket = Blueprint("ticket", __name__)

# ==================== CHARGEMENT MODÈLE IA ====================
try:
    priority_model = joblib.load("models/priority_model.pkl")
    priority_vectorizer = joblib.load("models/priority_vectorizer.pkl")
    priority_label_encoder = joblib.load("models/priority_label_encoder.pkl")
    print("✅ Modèle IA chargé")
except Exception as e:
    priority_model = None
    print(f"⚠️ Modèle non chargé: {e}")

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def predict_priority_hybrid(subject, body):
    text = f"{subject} {body}".lower()
    high_keywords = ["urgent", "asap", "critical", "blocking", "emergency", "down", "outage", "crash", "panne", "faille", "sécurité"]
    low_keywords = ["facture", "rembours", "billing", "low priority", "suggestion", "information", "impayée"]
    if any(kw in text for kw in high_keywords):
        return "high", 0.95
    if any(kw in text for kw in low_keywords):
        return "low", 0.95
    if priority_model is not None:
        try:
            cleaned = clean_text(f"{subject} {body}")
            X = priority_vectorizer.transform([cleaned])
            proba = priority_model.predict_proba(X)[0]
            confidence = float(max(proba))
            predicted_class = priority_model.predict(X)[0]
            priority = priority_label_encoder.inverse_transform([predicted_class])[0]
            return priority, confidence
        except Exception as e:
            print(f"Erreur IA: {e}")
    return "medium", 0.6

# ==================== ROUTES ====================

@ticket.route("/create", methods=["POST"])
@token_required
def create_ticket_route(current_user):
    data = request.json
    subject = data.get("subject", "")
    body = data.get("body", "")
    type_personnalise = data.get("type_personnalise", "")
    priority_predicted, confidence = predict_priority_hybrid(subject, body)
    priority = priority_predicted
    ticket_record = create_ticket(
        subject, body, priority, priority_predicted,
        user_id=str(current_user["_id"]),
        user_name=current_user.get("name", "Développeur"),
        user_email=current_user.get("email", ""),
        type_personnalise=type_personnalise,
        score_confiance=confidence
    )
    return jsonify({
        "message": "Ticket créé",
        "ticket": ticket_record,
        "priority": priority,
        "priority_predicted": priority_predicted,
        "confidence": confidence
    }), 201

@ticket.route("/my", methods=["GET"])
@token_required
def get_my_tickets(current_user):
    tickets = get_tickets_by_user(str(current_user["_id"]))
    return jsonify(tickets), 200

@ticket.route("/all", methods=["GET"])
@token_required
def get_all_tickets_route(current_user):
    if current_user.get("role") not in ["it_consultant", "it"]:
        return jsonify({"error": "Accès non autorisé"}), 403
    tickets = get_all_tickets()
    return jsonify(tickets), 200

@ticket.route("/<ticket_id>", methods=["GET"])
@token_required
def get_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    return jsonify(ticket_record), 200

@ticket.route("/<ticket_id>", methods=["PUT"])
@token_required
def update_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    data = request.json
    allowed_fields = ["priorite", "status", "description", "titre", "type_personnalise"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_data:
        return jsonify({"error": "Aucun champ valide à mettre à jour"}), 400
    updated = update_ticket(ticket_id, update_data)
    return jsonify({"message": "Ticket mis à jour", "ticket": updated}), 200

@ticket.route("/<ticket_id>/priority", methods=["PATCH"])
@token_required
def update_ticket_priority(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    new_priority = request.json.get("priority")
    if new_priority not in ["low", "medium", "high"]:
        return jsonify({"error": "Priority must be low, medium or high"}), 400
    update_data = {
        "priorite": new_priority,
        "priority_manual_override": True,
        "priority_updated_at": datetime.datetime.utcnow().isoformat()
    }
    updated = update_ticket(ticket_id, update_data)
    return jsonify({"message": "Priority updated", "ticket": updated}), 200

@ticket.route("/<ticket_id>", methods=["DELETE"])
@token_required
def delete_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    result = delete_ticket(ticket_id)
    return jsonify(result), 200

# ==================== ROUTE POUR L'ANALYSE IA ====================
@ticket.route("/predict", methods=["POST"])
def predict_route():
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "Missing 'text' field"}), 400
        
        text = data["text"]
        cleaned = clean_text(text)
        
        if priority_model is None:
            return jsonify({"prediction": "Moyenne", "confidence": 0.75})
        
        X = priority_vectorizer.transform([cleaned])
        proba = priority_model.predict_proba(X)[0]
        confidence = float(max(proba))
        predicted_class = priority_model.predict(X)[0]
        category = priority_label_encoder.inverse_transform([predicted_class])[0]
        
        category_map = {"high": "Haute", "medium": "Moyenne", "low": "Basse"}
        display_category = category_map.get(category, category)
        
        # Ajustement doux de la confiance (optionnel)
        if confidence < 0.5:
            confidence = 0.5 + (0.5 - confidence) * 0.3
        confidence = min(confidence, 0.95)
        confidence = round(confidence, 2)
        
        return jsonify({"prediction": display_category, "confidence": confidence})
    except Exception as e:
        print(f"Erreur dans predict_route: {str(e)}")
        return jsonify({"error": str(e)}), 500