from flask import Blueprint, request, jsonify
import joblib
from models.ticket_db import create_ticket, get_tickets_by_user, get_ticket_by_id, update_ticket, delete_ticket
from auth_middleware import token_required
from models.ticket_db import get_all_tickets 
import datetime

ticket = Blueprint("ticket", __name__)
ticket_model = joblib.load("models/ticket_model.pkl")

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
    
    if any(word in text for word in ["facture", "rembours", "billing", "paiement", "montant"]):
        priority = "low"
        ticket_type = "Billing"
    elif any(word in text for word in ["produit", "panne", "casse"]):
        priority = "medium"
        ticket_type = "Product Support"
    else:
        try:
            ticket_type = ticket_model.predict([text])[0]
            priority = priority_map.get(ticket_type, "medium")
        except:
            priority = "medium"
            ticket_type = "unknown"
    
    ticket_record = create_ticket(
        subject, body, priority,
        user_id=str(current_user["_id"]),
        type_personnalise=type_personnalise or ticket_type
    )
    return jsonify({
        "message": "Ticket créé",
        "ticket": ticket_record,
        "priority": priority,
        "type": ticket_type
    })

@ticket.route("/my", methods=["GET"])
@token_required
def get_my_tickets(current_user):
    tickets = get_tickets_by_user(str(current_user["_id"]))
    return jsonify(tickets)

@ticket.route("/<ticket_id>", methods=["GET"])
@token_required
def get_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if ticket_record and ticket_record.get("user_id") == str(current_user["_id"]):
        return jsonify(ticket_record)
    return jsonify({"error": "Ticket non trouvé"}), 404

@ticket.route("/<ticket_id>", methods=["PUT"])
@token_required
def update_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record or ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    data = request.json
    updated = update_ticket(ticket_id, data)
    return jsonify({"message": "Ticket mis à jour", "ticket": updated})

@ticket.route("/<ticket_id>/priority", methods=["PATCH"])
@token_required
def update_ticket_priority(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record or ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    new_priority = request.json.get("priority")
    if new_priority not in ["low", "medium", "high"]:
        return jsonify({"error": "Priority must be low, medium or high"}), 400
    update_data = {
        "priority": new_priority,
        "priority_manual_override": True,
        "priority_updated_at": datetime.datetime.utcnow().isoformat()
    }
    updated = update_ticket(ticket_id, update_data)
    return jsonify({"message": "Priority updated", "ticket": updated})

@ticket.route("/<ticket_id>", methods=["DELETE"])
@token_required
def delete_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if not ticket_record or ticket_record.get("user_id") != str(current_user["_id"]):
        return jsonify({"error": "Non autorisé"}), 403
    return jsonify(delete_ticket(ticket_id))
 # Ajouter en haut du fichier

@ticket.route("/all", methods=["GET"])
@token_required
def get_all_tickets_for_it(current_user):
    """Retourne tous les tickets (réservé aux IT Consultants)"""
    if current_user.get("role") not in ["it_consultant", "it"]:
        return jsonify({"error": "Accès non autorisé"}), 403
    tickets = get_all_tickets()  # ← utilise la fonction définie dans ticket_db
    return jsonify(tickets), 200