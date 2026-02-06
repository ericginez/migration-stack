#!/usr/bin/env python3
"""import_healthcare_dataset_to_mongodb.py

Objectif
--------
Importer un fichier CSV (ex: `healthcare_dataset.csv`) dans une collection MongoDB
en appliquant des conversions de types cohérentes (Age -> int, dates -> datetime, etc.)
et en insérant en lots pour de meilleures performances.

Points clés
-----------
- Lecture *streaming* : lecture du CSV ligne par ligne (pas de chargement complet en mémoire).
- Insertion *batch* : `insert_many()` par paquets (`--batch-size`).
- Vérification de connexion : `ping` MongoDB au démarrage (fail-fast).
- Préparation optionnelle : `--drop` (recrée la collection) / `--clear` (vide la collection).
- Index optionnels : création des index après import (souvent plus rapide).

Exemples
--------
Importer dans une base locale :
    python migration/import_healthcare_dataset_to_mongodb.py \
      --csv data/healthcare_dataset.csv \
      --mongo-uri mongodb://localhost:27017 \
      --db healthcare \
      --collection patients \
      --batch-size 1000 \
      --drop

Importer en mode "append" (ajout) :
    python migration/import_healthcare_dataset_to_mongodb.py \
      --csv data/healthcare_dataset.csv \
      --mongo-uri mongodb://localhost:27017 \
      --db healthcare \
      --collection patients
"""

import argparse
import csv
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from pymongo import ASCENDING, MongoClient


# ============================================================
# 1) Conversion de types (centralisée)
# ============================================================

def convert_type(field: str, v: Optional[str]) -> Any:
    """Convertir une valeur CSV (string) vers un type Python selon le champ.

    Cette fonction est *le point unique* où l'on définit la logique de typage.
    Elle est volontairement simple et déterministe, afin d'être testable.

    Paramètres
    ----------
    field:
        Nom de la colonne CSV.
    v:
        Valeur brute lue depuis le CSV (souvent une chaîne ; parfois None).

    Retour
    ------
    Any:
        Valeur convertie (int, float, datetime, str) ou None si manquante.
    """
    
    # Valeur absente : on retourne None (MongoDB stockera un null si présent)
    if v is None:
        return None

    # Nettoyage : retrait des espaces (" 42 " -> "42")
    s = v.strip()

    # Chaîne vide => considéré comme manquant
    if s == "":
        return None

    # Règles de conversion de type
    if field == "Age":
        return int(s)

    if field == "Billing Amount":
        return float(s)

    if field == "Room Number":
        return int(s)

    if field in ("Date of Admission", "Discharge Date"):
        # Format attendu : YYYY-MM-DD (ex: 2025-01-31)
        # Si le format n'est pas respecté, datetime.strptime lève ValueError
        return datetime.strptime(s, "%Y-%m-%d")

    # Règle de normalisation
    if field == "Name":
        # Normalisation simple de casse : "john DOE" -> "John Doe". Même norme que pour "Doctor".
        # Des doublons pourraient être cachés en absence de normalisation (MongoDB sensible à la casse).
        return s.lower().title()

    # Par défaut, retourner une chaîne propre
    return s


# ============================================================
# 2) Lecture CSV en streaming -> documents Python typés
# ============================================================

def iter_csv_rows(path: str) -> Iterable[Dict[str, Any]]:
    """Lire un CSV ligne par ligne et produire des documents (dict) prêts à insérer.

    Pourquoi un générateur ?
    ------------------------
    - Performance : pas de gros tableau en mémoire.
    - Robustesse : on peut interrompre/reprendre plus facilement.
    - Compatible avec la logique de batch (chunked()).
    """
    
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        # Si fieldnames est vide => CSV sans en-têtes / vide
        if not reader.fieldnames:
            raise ValueError("CSV vide ou en-têtes manquants.")

        for row in reader:
            # Conversion champ par champ
            doc = {k: convert_type(k, v) for k, v in row.items()}
            # Streaming : on émet le document
            yield doc


# ============================================================
# 3) Regroupement en lots (batch)
# ============================================================

def chunked(it: Iterable[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    """Regrouper des documents en lots de taille `size`.

    Pourquoi ?
    ----------
    - `insert_many()` est beaucoup plus efficace que `insert_one()` répété.
    - On contrôle la taille mémoire (un batch raisonnable).
    """
    
    # La taille de lot doit être un entier strictement positif.
    if size <= 0:
        raise ValueError("size doit être > 0")

    # Initialiser un lot vide.
    batch: List[Dict[str, Any]] = []

    # Lire et émettre `size` documents
    for item in it:
        batch.append(item)

        if len(batch) >= size:
            yield batch
            batch = []
    
    # Emettre le dernier lot si non vide
    if batch:
        yield batch


# ============================================================
# 4) Index MongoDB (optionnel, après import)
# ============================================================

def create_indexes(col) -> None:
    """Créer des index utiles pour les requêtes et/ou les checks sur les champs non texte.

    Stratégie
    ---------
    On préfère créer les index *après* un gros import :
    - plus rapide (moins de maintenance d'index pendant l'insertion)

    Index proposés
    --------------
    - Age
    - Billing Amount
    - Room Number
    - Date of Admission
    - Discharge Date
    - Index composé (Name, Date of Admission) pour recherches les doublons
    """
    
    # Indexes simples
    col.create_index([("Age", ASCENDING)], name="idx_age")
    col.create_index([("Billing Amount", ASCENDING)], name="idx_billing_amount")
    col.create_index([("Room Number", ASCENDING)], name="idx_room_number")
    col.create_index([("Date of Admission", ASCENDING)], name="idx_date_of_admission")
    col.create_index([("Discharge Date", ASCENDING)], name="idx_discharge_date")

    # Index composé
    col.create_index(
        [("Name", ASCENDING), ("Date of Admission", ASCENDING)],
        name="idx_name_date_of_admission",
    )


# ============================================================
# 5) Point d'entrée CLI
# ============================================================

def main() -> int:
    """Exécution principale (CLI) : parse args -> import -> (optionnel) index.

    Démarche globale:
    --------------------------------
    1) Parser la ligne de commande (argparse)
    2) Valider les paramètres (batch-size)
    3) Connecter MongoDB + ping (fail-fast)
    4) Préparer la collection (drop / clear / append)
    5) Importer : CSV -> docs -> batch -> insert_many
    6) (Optionnel) Créer les index si `--drop` et pas `--skip-indexes`
    7) Afficher un résumé
    """
    
    # (1) Arguments CLI
    parser = argparse.ArgumentParser(description="Importer un CSV dans MongoDB.")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV")
    parser.add_argument("--mongo-uri", required=True, help="URI MongoDB")
    parser.add_argument("--db", required=True, help="Nom de la base MongoDB")
    parser.add_argument("--collection", required=True, help="Nom de la collection")
    parser.add_argument("--batch-size", type=int, default=1000, help="Taille des lots (insert_many)")

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Supprimer la collection avant import (supprime aussi les index).",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Vider la collection sans la supprimer (conserve les index). Ignoré si --drop.",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Ne pas (re)créer les index après import (utile si tu veux indexer plus tard).",
    )

    args = parser.parse_args()

    # (2) Validation minimale
    if args.batch_size <= 0:
        raise ValueError("--batch-size doit être > 0")

    # (3) Connexion MongoDB + ping
    client = MongoClient(args.mongo_uri)
    client.admin.command("ping")  # fail-fast

    db = client[args.db]
    col = db[args.collection]

    # (4) Préparation collection
    if args.drop:
        # Drop : supprime collection + documents + index
        col.drop()
        col = db[args.collection]  # nouveau handle après drop
    elif args.clear:
        # Clear : supprime documents mais conserve les index
        col.delete_many({})

    # (5) Import
    total_inserted = 0
    for batch in chunked(iter_csv_rows(args.csv), args.batch_size):
        # ordered=False : tente d'insérer le maximum même si un doc échoue
        res = col.insert_many(batch, ordered=False)
        total_inserted += len(res.inserted_ids)

    # (6) Index (souvent après import, et seulement si on a recréé par un drop)
    if args.drop and (not args.skip_indexes):
        create_indexes(col)

    # (7) Résumé
    print(
        f"Import terminé : {total_inserted} documents insérés dans "
        f"{args.db}.{args.collection} (batch-size={args.batch_size})."
    )
    return 0

# Lancement du main
if __name__ == "__main__":
    # Gestion d'un Ctrl+C propre (retour 130)
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrompu par l'utilisateur.", file=sys.stderr)
        raise SystemExit(130)
