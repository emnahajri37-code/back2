#!/usr/bin/env python3
import re
import joblib
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
from datasets import load_dataset

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_data_sample(sample_size=5000):
    print(f"📥 Chargement d'un échantillon de {sample_size} tickets...")
    dataset = load_dataset("Tobi-Bueck/customer-support-tickets", split="train")
    df = dataset.to_pandas().sample(n=min(sample_size, len(dataset)), random_state=42)
    df['subject'] = df['subject'].fillna('')
    df['body'] = df['body'].fillna('')
    df['text'] = (df['subject'] + " " + df['body']).apply(clean_text)
    y = df['queue'].fillna('unknown')
    X = df['text']
    print("Distribution des classes :")
    print(y.value_counts())
    return X, y

def train_fast(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1,2), stop_words='english')),
        ('clf', LinearSVC(class_weight='balanced', dual='auto', max_iter=1000, random_state=42))
    ])
    print("🚀 Entraînement en cours... (max 30 secondes)")
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    print(f"✅ Accuracy: {accuracy_score(y_test, y_pred):.2%}")
    print(classification_report(y_test, y_pred, zero_division=0))
    return pipeline

if __name__ == "__main__":
    X, y = load_data_sample(sample_size=5000)  # ← petit échantillon
    model = train_fast(X, y)
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/ticket_model.pkl")
    # Sauvegarde aussi le mapping priorité
    priority_map = {
        "Technical Support": "high",
        "Product Support": "medium",
        "Billing": "low",
        "Account Management": "medium",
        "General Inquiry": "low"
    }
    joblib.dump(priority_map, "models/priority_map.pkl")
    print("✅ Modèle sauvegardé dans models/")