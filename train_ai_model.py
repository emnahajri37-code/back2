# train_ai_model.py
from datasets import load_dataset
from sklearn.preprocessing import LabelEncoder
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
import torch
from torch.utils.data import Dataset

# -------------------------------
# 1️⃣ Charger le dataset
# -------------------------------
print("Chargement du dataset…")
dataset = load_dataset("Tobi-Bueck/customer-support-tickets")
print("Colonnes disponibles:", dataset['train'].column_names)

# -------------------------------

# 2️⃣ Filtrer les données et préparer labels
# -------------------------------
dataset = dataset.filter(lambda x: x['type'] is not None)
labels = list(set(dataset['train']['type']))
print("Classes après filtrage:", labels)

# -------------------------------
# 3️⃣ Créer split train/test
# -------------------------------
dataset = dataset['train'].train_test_split(test_size=0.1, seed=42)
train_data = dataset['train']
test_data = dataset['test']

# Encoder les labels en nombres
label_encoder = LabelEncoder()
train_labels = label_encoder.fit_transform(train_data['type'])
test_labels = label_encoder.transform(test_data['type'])

# Préparer les textes en gérant les None
train_texts = [
    (t['subject'] if t['subject'] else "") + ". " + (t['body'] if t['body'] else "")
    for t in train_data
]
test_texts = [
    (t['subject'] if t['subject'] else "") + ". " + (t['body'] if t['body'] else "")
    for t in test_data
]
# -------------------------------
# 4️⃣ Tokenizer
# -------------------------------
model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)

train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=256)
test_encodings = tokenizer(test_texts, truncation=True, padding=True, max_length=256)

# -------------------------------
# 5️⃣ Dataset PyTorch
# -------------------------------
class TicketDataset(Dataset):
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

# -------------------------------
# 6️⃣ Modèle
# -------------------------------
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=len(labels)
)

# -------------------------------
# 7️⃣ Entraînement
# -------------------------------
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=50,
    load_best_model_at_end=True
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    tokenizer=tokenizer
)

trainer.train()

# -------------------------------
# 8️⃣ Sauvegarder le modèle
# -------------------------------
model.save_pretrained("./ticket_classifier_model")
tokenizer.save_pretrained("./ticket_classifier_model")
print("Modèle entraîné et sauvegardé !")