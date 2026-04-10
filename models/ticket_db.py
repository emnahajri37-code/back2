from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client["pfe_db"]
tickets_collection = db["tickets"]

def create_ticket(subject, body, priority, priority_predicted, user_id, user_name, user_email, type_personnalise="unknown", score_confiance=0.75):
    ticket = {
        "titre": subject,
        "description": body,
        "priorite": priority,                 # priorité actuelle (modifiable)
        "priorite_predite": priority_predicted, # priorité IA (non modifiable)
        "user_id": user_id,
        "user_name": user_name,
        "user_email": user_email,
        "type_personnalise": type_personnalise,
        "status": "En attente",
        "dateCreation": datetime.datetime.utcnow().isoformat(),
        "scoreConfiance": score_confiance
    }
    result = tickets_collection.insert_one(ticket)
    ticket["_id"] = str(result.inserted_id)
    return ticket

def get_tickets_by_user(user_id):
    tickets = list(tickets_collection.find({"user_id": user_id}))
    for t in tickets:
        t["_id"] = str(t["_id"])
    return tickets

def get_all_tickets():
    tickets = list(tickets_collection.find())
    for t in tickets:
        t["_id"] = str(t["_id"])
    return tickets

def get_ticket_by_id(ticket_id):
    try:
        ticket = tickets_collection.find_one({"_id": ObjectId(ticket_id)})
        if ticket:
            ticket["_id"] = str(ticket["_id"])
        return ticket
    except:
        return None

def update_ticket(ticket_id, data):
    tickets_collection.update_one({"_id": ObjectId(ticket_id)}, {"$set": data})
    return get_ticket_by_id(ticket_id)

def delete_ticket(ticket_id):
    result = tickets_collection.delete_one({"_id": ObjectId(ticket_id)})
    return {"deleted": result.deleted_count > 0}