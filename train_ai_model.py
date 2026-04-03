import pandas as pd
import numpy as np
import re
import joblib
import os

from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score

# =========================
# Nettoyage du texte
# =========================
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.strip()

# =========================
# Charger dataset HuggingFace
# =========================
def load_dataset_data(target_column='queue'):
    print("📥 Téléchargement du dataset...")
    
    dataset = load_dataset("Tobi-Bueck/customer-support-tickets")
    df = dataset["train"].to_pandas()

    print(f"✅ Dataset chargé : {len(df)} tickets")

    # Nettoyage colonnes
    df['subject'] = df['subject'].fillna('')
    df['body'] = df['body'].fillna('')

    # Combiner texte
    df['text'] = df['subject'] + " " + df['body']
    df['text'] = df['text'].apply(clean_text)

    # Target
    df[target_column] = df[target_column].fillna('unknown')

    X = df['text']
    y = df[target_column]

    print(f"🎯 Nombre de classes ({target_column}) : {y.nunique()}")

    return X, y

# =========================
# Train model
# =========================
def train_model(X, y):

    # Split intelligent
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    # Pipeline ML
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            max_features=20000,
            ngram_range=(1, 2),
            stop_words='english'
        )),
        ('classifier', LinearSVC())
    ])

    print("🚀 Entraînement du modèle...")
    pipeline.fit(X_train, y_train)

    # Test
    print("📊 Évaluation...")
    y_pred = pipeline.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    print(f"\n✅ Accuracy : {acc:.2%}")

    print("\n📄 Classification Report :")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Sauvegarde
    if not os.path.exists("models"):
        os.makedirs("models")

    joblib.dump(pipeline, "models/ticket_model.pkl")

    print("\n💾 Modèle sauvegardé dans models/ticket_model.pkl")

    return pipeline

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    TARGET = "queue"   # 🔥 tu peux changer en: "type" ou "priority"

    X, y = load_dataset_data(TARGET)
    model = train_model(X, y)

    if model:
        print("\n🎉 Training terminé avec succès !")
    else:
        print("\n❌ Erreur training")