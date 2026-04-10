from flask import Blueprint, request, jsonify
import joblib
from models.ticket_db import create_ticket, get_tickets_by_user, get_ticket_by_id, update_ticket, delete_ticket, get_all_tickets
from auth_middleware import token_required
import datetime

ticket = Blueprint("ticket", __name__)

# Modèle IA (optionnel)
try:
    ticket_model = joblib.load("models/ticket_model.pkl")
except:
    ticket_model = None
    print("⚠️ Modèle ticket_model.pkl non trouvé, utilisation règles par défaut")

priority_map = {
    "Technical Support": "high",
    "Product Support": "medium",
    "Billing": "low"
}

@ticket.route("/create", methods=["POST"])
@token_required
def create_ticket_route(current_user):
    data = request.json
    subject = data.get("subject", "")
    body = data.get("body", "")
    type_personnalise = data.get("type_personnalise", "")
    text = f"{subject} {body}".lower()
    
    # Règles de priorité
    if any(word in text for word in ["facture", "rembours", "billing", "paiement", "montant"]):
        priority = "low"
        ticket_type = "Billing"
    elif any(word in text for word in ["produit", "panne", "casse"]):
        priority = "medium"
        ticket_type = "Product Support"
    else:
        if ticket_model:
            try:
                ticket_type = ticket_model.predict([text])[0]
                priority = priority_map.get(ticket_type, "medium")
            except:
                priority = "medium"
                ticket_type = "unknown"
        else:
            priority = "medium"
            ticket_type = "unknown"
    
    ticket_record = create_ticket(
        subject, body, priority,
        user_id=str(current_user["_id"]),
        user_name=current_user.get("name", "Développeur"),
        type_personnalise=type_personnalise or ticket_type
    )
    return jsonify({
        "message": "Ticket créé",
        "ticket": ticket_record,
        "priority": priority,
        "type": ticket_type
    }), 201

@ticket.route("/my", methods=["GET"])
@token_required
def get_my_tickets(current_user):
    tickets = get_tickets_by_user(str(current_user["_id"]))
    return jsonify(tickets), 200

@ticket.route("/all", methods=["GET"])
@token_required
def get_all_tickets_route(current_user):
    """Route réservée aux IT Consultants"""
    if current_user.get("role") not in ["it_consultant", "it"]:
        return jsonify({"error": "Accès non autorisé"}), 403
    tickets = get_all_tickets()
    print(f"📋 Envoi de {len(tickets)} tickets à l'IT Consultant")
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
    print(f"🔵 Mise à jour du ticket {ticket_id}")
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    data = request.json
    print(f"   Données reçues: {data}")
    updated = update_ticket(ticket_id, data)
    return jsonify({"message": "Ticket mis à jour", "ticket": updated}), 200

@ticket.route("/<ticket_id>/priority", methods=["PATCH"])
@token_required
def update_ticket_priority(current_user, ticket_id):
    print(f"🔵 Changement priorité ticket {ticket_id}")
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    new_priority = request.json.get("priority")
    print(f"   Nouvelle priorité: {new_priority}")
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
    print(f"🔵 Suppression ticket {ticket_id}")
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record:
        return jsonify({"error": "Ticket non trouvé"}), 404
    if current_user.get("role") not in ["it_consultant", "it"] and ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    result = delete_ticket(ticket_id)
    return jsonify(result), 200