from pymongo import MongoClient

# Connexion MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["ticket_db"]
tickets_collection = db["tickets"]

# Mapping type → priorité
priority_map = {
    "Technical Support": "high",
    "Product Support": "medium",
    "Billing": "low"
}

print("🚀 Correction des tickets en cours...")

tickets = list(tickets_collection.find())

for t in tickets:
    old_value = t.get("priority")

    # Convertir ancien type → vraie priorité
    new_priority = priority_map.get(old_value, "medium")

    tickets_collection.update_one(
        {"_id": t["_id"]},
        {"$set": {"priority": new_priority}}
    )

    print(f"✔ Ticket {t['_id']} : {old_value} → {new_priority}")

print("\n✅ Tous les tickets sont corrigés !")