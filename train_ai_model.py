# fichier: train_ticket_classifier.py

from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

# 1️⃣ Charger le dataset
dataset = load_dataset("Tobi-Bueck/customer-support-tickets")

# Filtrer pour ne garder que les classes principales
valid_classes = ['Change', 'Incident', 'Problem', 'Request']
dataset = dataset.filter(lambda x: x['type'] in valid_classes)

# 2️⃣ Préparer les textes et labels
texts = []
labels = []
for subj, body, label in zip(dataset['train']['subject'], dataset['train']['body'], dataset['train']['type']):
    subj = subj if subj else ""
    body = body if body else ""
    texts.append(subj + ". " + body)
    labels.append(label)

# 3️⃣ Split train/test
X_train, X_test, y_train, y_test = train_test_split(
    texts, labels, test_size=0.2, random_state=42
)

# 4️⃣ Créer un pipeline TF-IDF + Logistic Regression
pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=5000, stop_words='english')),
    ('clf', LogisticRegression(max_iter=1000))
])

# 5️⃣ Entraîner le modèle
pipeline.fit(X_train, y_train)

# 6️⃣ Évaluer le modèle
y_pred = pipeline.predict(X_test)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# 7️⃣ Prédire un nouveau ticket
def predict_ticket(subject, body):
    text = (subject if subject else "") + ". " + (body if body else "")
    return pipeline.predict([text])[0]

# Exemple d'utilisation
nouveau_ticket = {
    "subject": "Problème avec l'impression réseau",
    "body": "L'imprimante du département marketing ne répond plus depuis ce matin."
}
prediction = predict_ticket(nouveau_ticket['subject'], nouveau_ticket['body'])
print("\nNouvelle prédiction:", prediction)