import pandas as pd
import re
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# Charger le dataset
data = pd.read_csv("ticket.csv")  # colonnes: subject, body, type

# Nettoyage et création du texte
data["subject"] = data["subject"].fillna("")
data["body"] = data["body"].fillna("")
data["text"] = data["subject"] + " " + data["body"]

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

data["text"] = data["text"].apply(clean_text)

# === CRÉATION ARTIFICIELLE DE LA PRIORITÉ À PARTIR DE RÈGLES ===
def assign_priority(text):
    text_lower = text.lower()
    high = ["urgent", "asap", "critical", "blocking", "emergency", "down", "outage"]
    low  = ["low priority", "not urgent", "suggestion", "minor"]
    if any(kw in text_lower for kw in high):
        return "high"
    elif any(kw in text_lower for kw in low):
        return "low"
    else:
        return "medium"

data["priority"] = data["text"].apply(assign_priority)

# Afficher la distribution
print("Distribution des priorités créées :")
print(data["priority"].value_counts())

# Encodage des labels
le = LabelEncoder()
y = le.fit_transform(data["priority"])

X_train, X_test, y_train, y_test = train_test_split(
    data["text"], y, test_size=0.2, random_state=42, stratify=y
)

# TF-IDF
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=15000,
    sublinear_tf=True
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Modèle
model = LogisticRegression(class_weight="balanced", C=1.0, max_iter=1000)
model.fit(X_train_vec, y_train)

# Évaluation (le modèle devrait être quasi parfait car il apprend les règles)
y_pred = model.predict(X_test_vec)
accuracy = (y_test == y_pred).mean()
print(f"Accuracy du modèle (sur règles) : {accuracy:.4f}")

# Sauvegarde
joblib.dump(model, "priority_model.pkl")
joblib.dump(vectorizer, "priority_vectorizer.pkl")
joblib.dump(le, "priority_label_encoder.pkl")
print("✅ Modèle priorité sauvegardé.")