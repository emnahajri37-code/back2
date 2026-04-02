from flask import Blueprint, request, jsonify
from models.ticket_model import create_ticket, get_all_tickets, get_ticket_by_id, update_ticket, delete_ticket

ticket = Blueprint("ticket", __name__)

# ✅ CREATE TICKET
@ticket.route("/tickets", methods=["POST"])
def create_ticket_route():
    data = request.json
    # Vérifier les champs obligatoires
    required_fields = ["title", "description", "user_id", "developer_name"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Champs manquants : {', '.join(missing_fields)}"}), 400

    ticket_id = create_ticket(data)
    return jsonify({
        "message": "Ticket créé",
        "id": ticket_id
    }), 201


# ✅ GET ALL TICKETS
@ticket.route("/tickets", methods=["GET"])
def get_all_tickets_route():
    tickets = get_all_tickets()
    return jsonify(tickets), 200


# ✅ GET ONE TICKET
@ticket.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket_route(ticket_id):
    ticket_data = get_ticket_by_id(ticket_id)
    if not ticket_data:
        return jsonify({"error": "Ticket non trouvé"}), 404
    return jsonify(ticket_data), 200


# ✅ UPDATE TICKET
@ticket.route("/tickets/<ticket_id>", methods=["PUT"])
def update_ticket_route(ticket_id):
    data = request.json
    success = update_ticket(ticket_id, data)
    if not success:
        return jsonify({"error": "Aucune modification ou ticket introuvable"}), 400
    return jsonify({"message": "Ticket mis à jour"}), 200


# ✅ DELETE TICKET
@ticket.route("/tickets/<ticket_id>", methods=["DELETE"])
def delete_ticket_route(ticket_id):
    success = delete_ticket(ticket_id)
    if not success:
        return jsonify({"error": "Ticket introuvable"}), 404
    return jsonify({"message": "Ticket supprimé"}), 200