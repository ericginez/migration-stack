FROM python:3.11-slim

WORKDIR /app

# -------------------------------------------------------------------
# Dépendances Python (pymongo)
# -------------------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -------------------------------------------------------------------
# Scripts applicatifs
# - import_healthcare_dataset_to_mongodb.py : migration (import CSV -> MongoDB)
# - integrity_checks_mongodb.py             : contrôles d'intégrité post-migration
# -------------------------------------------------------------------
COPY import_healthcare_dataset_to_mongodb.py /app/import_healthcare_dataset_to_mongodb.py
COPY integrity_checks_mongodb.py /app/integrity_checks_mongodb.py

# -------------------------------------------------------------------
# Entrypoint runtime générique (python)
# -------------------------------------------------------------------
ENTRYPOINT ["python"]
