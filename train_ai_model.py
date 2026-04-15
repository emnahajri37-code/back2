import pandas as pd
import re
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import warnings
warnings.filterwarnings('ignore')

# 1. Chargement et nettoyage
data = pd.read_csv("ticket.csv")
data["subject"] = data["subject"].fillna("")
data["body"] = data["body"].fillna("")
data["text"] = data["subject"] + " " + data["body"]

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

data["text"] = data["text"].apply(clean_text)

# 2. Règles de priorité (inchangées)
def assign_priority(text):
    text_lower = text.lower()
    high = ["urgent", "asap", "critical", "blocking", "emergency", "down", "outage", "crash", "plantage", "indisponible"]
    low  = ["low priority", "not urgent", "suggestion", "minor", "facture", "rembours", "billing", "info", "question"]
    if any(kw in text_lower for kw in high):
        return "high"
    elif any(kw in text_lower for kw in low):
        return "low"
    else:
        return "medium"

data["priority"] = data["text"].apply(assign_priority)
print("Distribution initiale :")
print(data["priority"].value_counts())

# 3. Équilibrage (sous-échantillonnage au minimum)
min_count = data["priority"].value_counts().min()
balanced = []
for p in data["priority"].unique():
    sub = data[data["priority"] == p]
    if len(sub) > min_count:
        sub = sub.sample(n=min_count, random_state=42)
    balanced.append(sub)
data_bal = pd.concat(balanced, ignore_index=True)
print("\nDistribution équilibrée :")
print(data_bal["priority"].value_counts())

# 4. Encodage
le = LabelEncoder()
y = le.fit_transform(data_bal["priority"])

# 5. Split
X_train, X_test, y_train, y_test = train_test_split(
    data_bal["text"], y, test_size=0.2, random_state=42, stratify=y
)

# 6. TF-IDF avec trigrammes
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 3),
    max_features=15000,
    sublinear_tf=True,
    min_df=2,
    max_df=0.9
)
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# 7. LinearSVC (très efficace sur le texte)
base_svc = LinearSVC(
    C=1.0,
    class_weight='balanced',
    max_iter=2000,
    dual='auto',
    random_state=42
)
# Calibration pour obtenir des probabilités
model = CalibratedClassifierCV(base_svc, method='sigmoid', cv=3)
model.fit(X_train_vec, y_train)

# 8. Évaluation
y_pred = model.predict(X_test_vec)
acc = (y_test == y_pred).mean()
print(f"\n🎯 Accuracy : {acc:.4f}")
print("\nRapport de classification :")
print(classification_report(y_test, y_pred, target_names=le.classes_))

proba = model.predict_proba(X_test_vec)
max_proba = np.max(proba, axis=1)
print(f"\n📊 Confiance moyenne : {max_proba.mean():.2f}")
print(f"   Médiane : {np.median(max_proba):.2f}")
print(f"   Min : {max_proba.min():.2f}")
print(f"   Max : {max_proba.max():.2f}")

# 9. Sauvegarde
joblib.dump(model, "models/priority_model.pkl")
joblib.dump(vectorizer, "models/priority_vectorizer.pkl")
joblib.dump(le, "models/priority_label_encoder.pkl")
print("\n💾 Modèle LinearSVC calibré sauvegardé")