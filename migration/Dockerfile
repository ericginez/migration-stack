FROM python:3.11-slim

WORKDIR /app

# Dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Script de migration
COPY import_healthcare_dataset_to_mongodb.py /app/import_healthcare_dataset_to_mongodb.py

ENTRYPOINT ["python", "/app/import_healthcare_dataset_to_mongodb.py"]
