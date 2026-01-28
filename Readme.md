# MongoDB Data Migration Stack

Projet réalisé dans le cadre de la formation **Data Engineer – OpenClassrooms**.  
L’objectif est de mettre en place une **migration de données industrialisée** vers MongoDB,
reposant sur **Docker Compose**, un **conteneur batch Python**, des **tests unitaires** et une **CI GitHub Actions**.

---

## Objectifs du projet

- Déployer une base **MongoDB** de manière reproductible
- Importer un jeu de données CSV dans MongoDB via un script Python
- Séparer clairement :
  - le service de base de données (long-running),
  - le job de migration (batch / one-shot)
- Automatiser les tests unitaires
- Mettre en place une **intégration continue (CI)**

---

## Architecture

Le projet repose sur deux services Docker distincts :

- **MongoDB**
  - déployé via une image officielle
  - persistance assurée par un volume Docker
  - protégé par authentification
- **Migration Python**
  - conteneur batch exécuté une seule fois
  - importe les données CSV
  - applique des règles de normalisation et de validation
  - crée les index MongoDB
  - s’arrête automatiquement après exécution

Les services sont orchestrés via **Docker Compose profiles**.

---

## Arborescence du projet

```
migration-stack/
├── docker-compose.yml
├── .env
├── Readme.md
├── data/
│   └── healthcare_dataset.csv
├── migration/
│   ├── __init__.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── import_healthcare_dataset_to_mongodb.py
├── unit_tests/
│   ├── test_convert_type.py
│   └── test_smoke_import_module.py
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Pré-requis

- Docker ≥ 20.x
- Docker Compose v2
- Python ≥ 3.11 (uniquement pour exécuter les tests en local)

---

## Lancement du projet

### Démarrer MongoDB
```
docker compose --profile db up -d
```

### Lancer la migration
```
docker compose --profile migrate up --build
```

### Arrêt
```
docker compose down --remove-orphans
```

---

## Tests unitaires
```
python -m unittest discover -s unit_tests -p "test_*.py" -v
```
