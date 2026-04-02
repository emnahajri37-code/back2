from flask import Blueprint, request, jsonify
from models.ticket_model import *

ticket = Blueprint("ticket", __name__)

# ✅ CREATE TICKET (developer)
@ticket.route("/tickets", methods=["POST"])
def create_ticket_route():
    data = request.json
    ticket_id = create_ticket(data)

    return jsonify({
        "message": "Ticket créé",
        "id": ticket_id
    })


# ✅ GET ALL TICKETS (IT dashboard)
@ticket.route("/tickets", methods=["GET"])
def get_tickets():
    return jsonify(get_all_tickets())


# ✅ GET ONE TICKET
@ticket.route("/tickets/<id>", methods=["GET"])
def get_ticket_route(id):
    ticket = get_ticket_by_id(id)

    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify(ticket)


# ✅ UPDATE TICKET (IT change status)
@ticket.route("/tickets/<id>", methods=["PUT"])
def update_ticket_route(id):
    data = request.json
    update_ticket(id, data)

    return jsonify({"message": "Ticket updated"})


# ✅ DELETE TICKET
@ticket.route("/tickets/<id>", methods=["DELETE"])
def delete_ticket_route(id):
    delete_ticket(id)
    return jsonify({"message": "Ticket deleted"})