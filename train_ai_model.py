import pandas as pd
import re
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

<<<<<<< HEAD
# Charger le dataset
data = pd.read_csv("ticket.csv")  # colonnes: subject, body, type
=======
print("🚀 Chargement du dataset...")

# ==========================
# LOAD DATA
# ==========================

if not os.path.exists("ticket.csv"):
    print("📥 Téléchargement dataset...")

    dataset = load_dataset("Tobi-Bueck/customer-support-tickets")
    data = dataset["train"].to_pandas()

    data = data[["subject", "body", "type"]]
    data.to_csv("ticket.csv", index=False, encoding="utf-8")

    print("✅ ticket.csv créé")
else:
    print("📂 ticket.csv déjà ")

data = pd.read_csv("ticket.csv")

# ==========================
# CLEANING
# ==========================
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b

# Nettoyage et création du texte
data["subject"] = data["subject"].fillna("")
data["body"] = data["body"].fillna("")
<<<<<<< HEAD
=======
data["type"] = data["type"].fillna("unknown")

# fusion texte
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b
data["text"] = data["subject"] + " " + data["body"]

print("\n📊 Distribution des classes:")
print(data["type"].value_counts())

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

data["text"] = data["text"].apply(clean_text)

<<<<<<< HEAD
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
=======
# ==========================
# (OPTIONNEL MAIS IMPORTANT) LIMITATION CLASSES TROP RARES
# ==========================

# garder uniquement classes fréquentes
min_samples = 500
value_counts = data["type"].value_counts()
valid_classes = value_counts[value_counts >= min_samples].index
data = data[data["type"].isin(valid_classes)]

# ==========================
# SPLIT
# ==========================
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b

data["priority"] = data["text"].apply(assign_priority)

# Afficher la distribution
print("Distribution des priorités créées :")
print(data["priority"].value_counts())

# Encodage des labels
le = LabelEncoder()
y = le.fit_transform(data["priority"])

X_train, X_test, y_train, y_test = train_test_split(
<<<<<<< HEAD
    data["text"], y, test_size=0.2, random_state=42, stratify=y
=======
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b
)

# TF-IDF
<<<<<<< HEAD
vectorizer = TfidfVectorizer(
    stop_words="english",
    ngram_range=(1, 2),
    max_features=15000,
=======
# ==========================

word_tfidf = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1, 2),   # 🔥 réduit overfitting
    max_features=30000,
    sublinear_tf=True,
    min_df=2,
    max_df=0.9
)

char_tfidf = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(3, 5),
    max_features=20000,
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b
    sublinear_tf=True
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

<<<<<<< HEAD
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
=======
log_reg = LogisticRegression(
    max_iter=2000,
    class_weight="balanced",
    C=3.0,
    solver="saga"
)

svm = LinearSVC(
    class_weight="balanced",
    C=1.0
)

calibrated_svm = CalibratedClassifierCV(svm, method="sigmoid")

# ==========================
# PIPELINES
# ==========================

pipeline_word = Pipeline([
    ("tfidf", word_tfidf),
    ("scaler", MaxAbsScaler()),
    ("clf", log_reg)
])

pipeline_char = Pipeline([
    ("tfidf", char_tfidf),
    ("clf", calibrated_svm)
])

# ==========================
# ENSEMBLE
# ==========================

ensemble = VotingClassifier(
    estimators=[
        ("word_lr", pipeline_word),
        ("char_svm", pipeline_char)
    ],
    voting="soft",
    weights=[2, 3]
)

# ==========================
# TRAINING
# ==========================

print("\n🔥 Entraînement...")
ensemble.fit(X_train, y_train)
print("✅ Terminé")

# ==========================
# EVALUATION
# ==========================

y_pred = ensemble.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)

print("\n🎯 Accuracy:", accuracy)
print("\n📊 Rapport:\n", classification_report(y_test, y_pred))

# ==========================
# SAVE MODEL
# ==========================

joblib.dump(ensemble, "model_pipeline.pkl")
print("\n💾 Modèle sauvegardé")

# ==========================
# TEST
# ==========================

test_text = ["Server is down and not responding"]
print("\n🚀 Test:", ensemble.predict(test_text))
>>>>>>> eede3ffe8f73a2713431e8997e005dd09652e46b
