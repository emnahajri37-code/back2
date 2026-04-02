from config.db import tickets_collection
from bson import ObjectId

# ✅ CREATE
def create_ticket(data):
    """
    Crée un nouveau ticket dans la collection.
    Les champs manquants auront des valeurs par défaut.
    """
    ticket = {
        "title": data.get("title", "Titre non fourni"),
        "description": data.get("description", ""),
        "type": data.get("type", "général"),
        "created_by": data.get("user_id", "anonyme"),
        "developer_name": data.get("developer_name", "non assigné"),
        "status": "open"
    }
    result = tickets_collection.insert_one(ticket)
    return str(result.inserted_id)


# ✅ GET ALL
def get_all_tickets():
    """
    Retourne tous les tickets avec les _id convertis en string.
    """
    tickets = []
    for t in tickets_collection.find():
        t["_id"] = str(t["_id"])
        tickets.append(t)
    return tickets


# ✅ GET ONE
def get_ticket_by_id(ticket_id):
    """
    Retourne un ticket selon son _id.
    """
    try:
        ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
        if ticket:
            ticket["_id"] = str(ticket["_id"])
        return ticket
    except Exception:
        return None  # si ObjectId invalide ou ticket introuvable


# ✅ UPDATE
def update_ticket(ticket_id, data):
    """
    Met à jour un ticket existant.
    Seules les clés valides sont mises à jour.
    """
    allowed_fields = ["title", "description", "type", "status", "developer_name"]
    update_data = {k: data[k] for k in allowed_fields if k in data}

    if not update_data:
        return False  # rien à mettre à jour

    result = tickets_collection.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": update_data}
    )
    return result.modified_count > 0


# ✅ DELETE
def delete_ticket(ticket_id):
    """
    Supprime un ticket selon son _id.
    """
    try:
        result = tickets_collection.delete_one({"_id": ObjectId(ticket_id)})
        return result.deleted_count > 0
    except Exception:
        return False