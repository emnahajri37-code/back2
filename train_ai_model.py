import pandas as pd
import re
import joblib
import os

from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import VotingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import MaxAbsScaler

print("🚀 Chargement du dataset...")

# ==========================
# LOAD DATA
# ==========================

if not os.path.exists("ticket.csv"):
    print("📥 Téléchargement depuis Hugging Face...")

    dataset = load_dataset("Tobi-Bueck/customer-support-tickets")
    data = dataset["train"].to_pandas()

    data = data[["subject", "body", "type"]]
    data.to_csv("ticket.csv", index=False, encoding="utf-8")

    print("✅ ticket.csv créé")
else:
    print("📂 ticket.csv déjà موجود")

data = pd.read_csv("ticket.csv")

# ==========================
# CLEANING
# ==========================

data["subject"] = data["subject"].fillna("")
data["body"] = data["body"].fillna("")
data["type"] = data["type"].fillna("unknown")

data = data.sample(frac=1, random_state=42)

data["text"] = data["subject"] + " " + data["body"]

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\d+", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

data["text"] = data["text"].apply(clean_text)

# ==========================
# SPLIT
# ==========================

X = data["text"]
y = data["type"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ==========================
# TF-IDF
# ==========================

word_tfidf = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1,3),
    max_features=50000,
    stop_words=None,
    sublinear_tf=True,
    min_df=2,
    max_df=0.9
)

char_tfidf = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(3,5),
    max_features=30000,
    sublinear_tf=True
)

# ==========================
# MODELS
# ==========================

# Logistic Regression (stable)
model_lr = LogisticRegression(
    max_iter=5000,
    class_weight="balanced",
    C=5.0,
    solver="saga"
)

# Linear SVM with calibration (no warning)
svm = LinearSVC(
    class_weight="balanced",
    C=1.2
)

calibrated_svm = CalibratedClassifierCV(svm, method="sigmoid")

# ==========================
# PIPELINES
# ==========================

pipeline_word = Pipeline([
    ("tfidf", word_tfidf),
    ("scaler", MaxAbsScaler()),
    ("clf", model_lr)
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