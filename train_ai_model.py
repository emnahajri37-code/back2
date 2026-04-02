# train_ai_model.py

# 🔹 Librairies
from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from transformers import DistilBertTokenizerFast, DistilBertForSequenceClassification, Trainer, TrainingArguments
import torch
import joblib
import os

# 🔹 1️⃣ Charger le dataset
print("Chargement du dataset...")
dataset = load_dataset("Tobi-Bueck/customer-support-tickets")

# On utilise la colonne "text" pour la description et "category" pour le label
texts = dataset['train']['ticket']
labels = dataset['train']['category']


# 🔹 2️⃣ Encoder les labels
label_encoder = LabelEncoder()
encoded_labels = label_encoder.fit_transform(labels)

# Sauvegarde de l'encodeur pour l'utilisation plus tard
os.makedirs("ticket_classifier", exist_ok=True)
joblib.dump(label_encoder, "ticket_classifier/label_encoder.pkl")
print("Label encoder sauvegardé.")

# 🔹 3️⃣ Diviser en train/test
train_texts, test_texts, train_labels, test_labels = train_test_split(
    texts, encoded_labels, test_size=0.2, random_state=42
)

# 🔹 4️⃣ Tokenizer
tokenizer = DistilBertTokenizerFast.from_pretrained("distilbert-base-uncased")
train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
test_encodings = tokenizer(test_texts, truncation=True, padding=True, max_length=128)

# 🔹 5️⃣ Dataset PyTorch
class TicketDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels
    def __len__(self):
        return len(self.labels)
    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

train_dataset = TicketDataset(train_encodings, train_labels)
test_dataset = TicketDataset(test_encodings, test_labels)

# 🔹 6️⃣ Charger le modèle
model = DistilBertForSequenceClassification.from_pretrained(
    "distilbert-base-uncased",
    num_labels=len(label_encoder.classes_)
)

# 🔹 7️⃣ Définir les paramètres d'entraînement
training_args = TrainingArguments(
    output_dir="./ticket_classifier",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=50,
    load_best_model_at_end=True,
    metric_for_best_model="accuracy"
)

# 🔹 8️⃣ Trainer
from transformers import Trainer, EvalPrediction
from sklearn.metrics import accuracy_score

def compute_metrics(p: EvalPrediction):
    preds = p.predictions.argmax(-1)
    return {"accuracy": accuracy_score(p.label_ids, preds)}

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=compute_metrics
)

# 🔹 9️⃣ Entraîner le modèle
print("Début de l'entraînement...")
trainer.train()

# 🔹 10️⃣ Sauvegarder le modèle et le tokenizer
model.save_pretrained("./ticket_classifier")
tokenizer.save_pretrained("./ticket_classifier")
print("Modèle et tokenizer sauvegardés dans ./ticket_classifier")