from flask import Blueprint, request, jsonify
import joblib
from models.ticket_db import create_ticket, get_all_tickets, get_ticket_by_id, update_ticket, delete_ticket
from auth_middleware import token_required

ticket = Blueprint("ticket", __name__)

ticket_model = joblib.load("models/ticket_model.pkl")

priority_map = {
    "Technical Support": "high",
    "Product Support": "medium",
    "Billing": "low"
}

from auth_middleware import token_required   # ← import indispensable

@ticket.route("/create", methods=["POST"])
@token_required
def create_ticket_route(current_user):
    data = request.json
    subject = data.get("subject", "")
    body = data.get("body", "")
    text = f"{subject} {body}".lower()
    
    # Détection de mots-clés pour priorité basse
    if any(word in text for word in ["facture", "rembours", "billing", "paiement", "montant"]):
        priority = "low"
        ticket_type = "Billing"
    elif any(word in text for word in ["produit", "panne", "casse"]):
        priority = "medium"
        ticket_type = "Product Support"
    else:
        # Fallback : modèle ou défaut
        try:
            ticket_type = ticket_model.predict([text])[0]
            priority = priority_map.get(ticket_type, "medium")
        except:
            priority = "medium"
            ticket_type = "unknown"
    
    ticket_record = create_ticket(subject, body, priority, user_id=str(current_user["_id"]))
    return jsonify({
        "message": "Ticket créé",
        "ticket": ticket_record,
        "priority": priority,
        "type": ticket_type
    })
@ticket.route("/", methods=["GET"])
@token_required
def get_tickets_route(current_user):
    tickets = get_all_tickets()
    return jsonify(tickets)

@ticket.route("/<ticket_id>", methods=["GET"])
@token_required
def get_ticket_route(current_user, ticket_id):
    ticket_record = get_ticket_by_id(ticket_id)
    if ticket_record:
        return jsonify(ticket_record)
    return jsonify({"error": "Ticket non trouvé"}), 404

@ticket.route("/<ticket_id>", methods=["PUT"])
@token_required
def update_ticket_route(current_user, ticket_id):
    data = request.json
    updated_ticket = update_ticket(ticket_id, data)
    if updated_ticket:
        return jsonify({"message": "Ticket mis à jour", "ticket": updated_ticket})
    return jsonify({"error": "Ticket non trouvé"}), 404

@ticket.route("/<ticket_id>", methods=["DELETE"])
@token_required
def delete_ticket_route(current_user, ticket_id):
    return jsonify(delete_ticket(ticket_id))