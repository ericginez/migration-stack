# MongoDB Data Migration Stack

## Contexte de la mission

L’objectif est de concevoir une **chaîne complète de migration de données** vers MongoDB, incluant :
- l’import de données CSV,
- la validation du code par des tests unitaires automatisés,
- le contrôle de la qualité des données via des tests d’intégrité.

---

## Objectifs techniques

- Migrer un jeu de données CSV vers MongoDB de manière fiable et performante
- Garantir la qualité du code (tests unitaires + CI)
- Vérifier la qualité des données stockées (tests d’intégrité)
- Utiliser Docker pour assurer la reproductibilité
- Fournir une documentation claire et exploitable

---

## Architecture du projet

Le projet repose sur **trois services Docker distincts**, orchestrés via Docker Compose et des *profiles*.

### 1. MongoDB (`mongodb`)
- Base de données MongoDB
- Service long-running
- Authentification activée
- Healthcheck MongoDB
- Persistance via volume Docker

### 2. Migration des données (`migrate_healthcare`)
- Service batch (one-shot)
- Exécute le script `import_healthcare_dataset_to_mongodb.py`
- Rôles :
  - lecture du CSV par lots
  - nettoyage et typage des données
  - insertion performante dans MongoDB
- S’arrête automatiquement après la migration

### 3. Tests d’intégrité (`integrity_checks`)
- Service batch (one-shot)
- Exécute le script `integrity_checks_mongodb.py`
- Vérifie :
  - valeurs manquantes
  - types des champs
  - doublons métier
  - règles de cohérence (sanity checks)
- Ne modifie jamais les données
- Exécuté **hors CI**, à la demande

---

## Arborescence du projet (commentée)

```text
migration-stack/
├── docker-compose.yml            				# Orchestration Docker des services
├── .env                          				# Variables d’environnement (MongoDB)
├── .gitignore                    				# Fichiers exclus du versionnement
├── README.md                     				# Documentation du projet
├── data/
│   └── healthcare_dataset.csv    				# Données source CSV
├── migration/
│   ├── Dockerfile                				# Image Python (migration + intégrité)
│   ├── requirements.txt          				# Dépendances Python
│   ├── import_healthcare_dataset_to_mongodb.py	# Script de migration
│   ├── integrity_checks_mongodb.py             # Tests d’intégrité
│   └── __init__.py               				# Déclaration du package Python
├── unit_tests/
│   ├── test_convert_type.py      				# Tests unitaires des conversions
│   └── test_smoke_import_module.py 			# Test de chargement du module
└── .github/workflows/
    └── ci.yml                    				# Pipeline CI (tests unitaires)
```

---

## Lancement du projet

### 1️ Démarrer MongoDB

```bash
docker compose --profile db up -d
```

---

### 2️ Lancer la migration des données

```bash
docker compose --profile migrate up --build
```

---

### 3️ Lancer les tests d’intégrité (optionnel)

```bash
docker compose --profile integrity up --build
```

Alternative :
```bash
docker compose run --rm integrity_checks --build
```

---

### Arrêter l’environnement

```bash
docker compose down --remove-orphans
```

---

## Tests

### Tests unitaires (CI)
- Exécutés automatiquement via GitHub Actions
- Basés sur le module `unittest`
- Garantissent la stabilité du code Python

### Tests d’intégrité (hors CI)
- Exécutés manuellement dans un service dédié
- Dépendent d’une base MongoDB réelle
- Vérifient la qualité métier des données

---

## CI – GitHub Actions

Le pipeline CI :
- s’exécute à chaque `push` et `pull_request`
- teste la compatibilité Python 3.11 et 3.12
- exécute uniquement les tests unitaires

Les tests d’intégrité sont volontairement exclus de la CI.

---

## Choix techniques et justification

- **Docker** : reproductibilité et isolation
- **MongoDB** : base NoSQL adaptée aux données semi-structurées
- **Tests unitaires** : validation rapide et automatisée
- **Tests d’intégrité séparés** : contrôle qualité métier réaliste
- **Profiles Docker Compose** : exécution modulaire et flexible

---

## Auteur

**Eric Ginez**  
