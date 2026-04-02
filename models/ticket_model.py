from config.db import tickets_collection
from bson import ObjectId

# ✅ CREATE
def create_ticket(data):
    ticket = {
        "title": data["title"],
        "description": data["description"],
        "type": data["type"],
        "created_by": data["user_id"],
        "developer_name": data["developer_name"],
        "status": "open"
    }
    result = tickets_collection.insert_one(ticket)
    return str(result.inserted_id)


# ✅ GET ALL
def get_all_tickets():
    tickets = []
    for t in tickets_collection.find():
        t["_id"] = str(t["_id"])
        tickets.append(t)
    return tickets


# ✅ GET ONE
def get_ticket_by_id(ticket_id):
    ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
    if ticket:
        ticket["_id"] = str(ticket["_id"])
    return ticket


# ✅ UPDATE
def update_ticket(ticket_id, data):
    update_data = {}

    if "status" in data:
        update_data["status"] = data["status"]

    tickets_collection.update_one(
        {"_id": ObjectId(ticket_id)},
        {"$set": update_data}
    )


# ✅ DELETE
def delete_ticket(ticket_id):
    tickets_collection.delete_one({"_id": ObjectId(ticket_id)})