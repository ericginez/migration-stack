# Migration de données Healthcare vers MongoDB (Docker Compose)

## 🎯 Objectif
Ce projet permet de **déployer MongoDB** et d’**exécuter une migration de données CSV vers MongoDB** à l’aide de **Docker Compose**.

L’architecture suit un pattern Data Engineering standard :
- un service **MongoDB** (long-running),
- un service **de migration batch** (one-shot).

---

## 🧱 Architecture

- **MongoDB**
  - Image officielle `mongo:7`
  - Données persistées via un volume Docker
  - Healthcheck intégré

- **Migration Healthcare**
  - Image Python construite via un `Dockerfile`
  - Script de migration CSV → MongoDB
  - Exécution unique (batch)
  - Dépend de MongoDB (attente de l’état *healthy*)

---

## 📁 Arborescence du projet

```text
migration-stack/
├── docker-compose.yml
├── .env
├── data/
│   └── healthcare_dataset.csv
└── migration/
    ├── Dockerfile
    ├── requirements.txt
    └── import_healthcare_dataset_to_mongodb.py
```

---

## ⚙️ Configuration

### Fichier `.env`

```env
MONGO_INITDB_ROOT_USERNAME=root
MONGO_INITDB_ROOT_PASSWORD=rootpw

MONGO_URI=mongodb://root:rootpw@mongodb:27017/?authSource=admin

MONGO_DB=healthcare
MONGO_COLLECTION=patients

CSV_PATH=/data/healthcare_dataset.csv
```

---

## 🚀 Lancement du projet

### 1️ Démarrer MongoDB

```bash
docker compose up -d --build mongodb
```

MongoDB :
- démarre en arrière-plan,
- devient *healthy* après le healthcheck,
- conserve les données via un volume Docker.

---

### 2️ Lancer la migration de données

```bash
docker compose run --rm migrate_healthcare
```

La migration effectue :
- la connexion à MongoDB,
- la suppression éventuelle de la collection cible,
- l’import du CSV,
- la création des index,
- puis s’arrête automatiquement.

---

### 3️ Vérifier l’état des services

```bash
docker compose ps
```

---

## 🧪 Connexion à MongoDB (optionnel)

MongoDB est exposé sur le port `27017` pour faciliter le debug local.

Depuis la machine hôte :

```bash
mongosh mongodb://root:rootpw@localhost:27017/?authSource=admin
```

---

## 🧹 Arrêt et nettoyage

### Arrêter les services (sans perdre les données)

```bash
docker compose down
```

### Arrêter et supprimer les données MongoDB (⚠️ destructif)

```bash
docker compose down -v
```

---

## 📝 Notes importantes

- Le service `migrate_healthcare` est un **job batch** :
  - il s’exécute une fois,
  - il se termine avec un code de sortie (0 en cas de succès).
- L’option `--abort-on-container-exit` n’est **pas recommandée** ici.
- La variable `MONGO_URI` est définie dans `.env` pour éviter toute ambiguïté lors de la substitution Docker Compose.

---

## 🧠 Bonnes pratiques appliquées

- Séparation service long-running / batch
- Healthcheck MongoDB
- Configuration centralisée dans `.env`
- Conteneur de migration éphémère
- Volumes Docker pour la persistance

---