# MongoDB Data Migration Stack

Projet réalisé dans le cadre de la formation **Data Engineer – OpenClassrooms**.  
L’objectif est de mettre en place une **migration de données industrialisée** vers MongoDB,
reposant sur **Docker Compose**, un **conteneur batch Python**, des **tests unitaires**, des **tests d’intégrité des données**
et une **intégration continue (CI) via GitHub Actions**.

---

## Objectifs du projet

- Déployer une base **MongoDB** de manière reproductible
- Importer un jeu de données CSV dans MongoDB via un script Python
- Séparer clairement :
  - le service de base de données (long-running),
  - le job de migration (batch / one-shot)
- Mettre en place :
  - des **tests unitaires** (logique métier Python)
  - des **tests d’intégrité des données** (qualité des données MongoDB)
- Automatiser l’ensemble via une **CI GitHub Actions**

---

## Architecture

Le projet repose sur deux services Docker distincts :

### MongoDB
- Déployé via l’image officielle MongoDB
- Persistance assurée par un volume Docker
- Authentification activée
- Healthcheck basé sur une commande `ping` MongoDB

### Migration Python
- Conteneur batch exécuté une seule fois
- Importe les données CSV dans MongoDB
- Applique des règles de normalisation et de typage
- Crée les index MongoDB
- S’arrête automatiquement après exécution

Les services sont orchestrés via **Docker Compose profiles** (`db`, `migrate`).

---

## Arborescence du projet

```
migration-stack/
├── .github/
│   └── workflows/
│       └── ci.yml              # Pipeline CI GitHub Actions
├── data/
│   └── healthcare_dataset.csv  # Données source
├── migration/
│   ├── __init__.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── import_healthcare_dataset_to_mongodb.py
├── unit_tests/
│   ├── test_convert_type.py
│   └── test_smoke_import_module.py
├── integrity_checks_mongodb.py # Tests d’intégrité des données
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md
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

### Arrêter les services
```
docker compose down --remove-orphans
```

---

## Tests unitaires (local)

Les tests unitaires valident la logique Python (conversion de types, normalisation, imports).

```
python -m unittest discover -s unit_tests -p "test_*.py" -v
```

---

## Tests d’intégrité des données

Les tests d’intégrité vérifient la **qualité des données stockées dans MongoDB** après ingestion :
- champs obligatoires présents
- types de données corrects
- règles de cohérence simples (sanity checks)

Exécution manuelle :
```
python integrity_checks_mongodb.py   --mongo-uri "<MONGO_URI>"   --db "<DB_NAME>"   --collection "<COLLECTION_NAME>"   --fail-on-missing   --fail-on-type   --fail-on-sanity
```

---

## Intégration Continue (CI)

Le pipeline **GitHub Actions** exécute automatiquement à chaque push ou pull request sur `main` :

1. Installation de Python
2. Installation des dépendances
3. Exécution des tests unitaires
4. Démarrage d’un service MongoDB
5. Seed de la base avec un échantillon de données
6. Exécution des tests d’intégrité en mode strict

Toute anomalie de code ou de données entraîne l’échec du pipeline.

---

## Bonnes pratiques mises en œuvre

- Séparation claire **ETL / tests unitaires / qualité des données**
- Pipeline CI reproductible
- Utilisation de Docker pour garantir la portabilité
- Vérification explicite de la qualité des données

---

## Contexte pédagogique

Ce projet s’inscrit dans le cadre du parcours **Data Engineer OpenClassrooms**  
et illustre une approche professionnelle de **migration de données**, **data quality**
et **industrialisation des pipelines**.
