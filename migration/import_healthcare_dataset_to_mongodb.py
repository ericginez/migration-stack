#!/usr/bin/env python3
import argparse
import csv
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from pymongo import ASCENDING, MongoClient


# ============================================================
# Conversion de type
# ============================================================

def convert_type(field: str, v: Optional[str]) -> Any:
    """
    Conversions de type implémentées :
      - Age                -> int
      - Billing Amount     -> float (séparateur '.')
      - Room Number        -> int
      - Date of Admission  -> date (YYYY-MM-DD)
      - Discharge Date     -> date (YYYY-MM-DD)
      - valeurs vides      -> None
      - Name               -> Normalisation de la casse
      - autres champs      -> str nettoyé
    """
    if v is None:
        return None

    s = v.strip()
    if s == "":
        return None

    if field == "Age":
        return int(s)

    if field == "Billing Amount":
        return float(s)

    if field == "Room Number":
        return int(s)

    if field in ("Date of Admission", "Discharge Date"):
        return datetime.strptime(s, "%Y-%m-%d")

    if field == "Name":
        return s.lower().title()

    return s


# ============================================================
# Lecture CSV en streaming
# ============================================================

def iter_csv_rows(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("CSV vide ou en-têtes manquants.")

        for row in reader:
            yield {k: convert_type(k, v) for k, v in row.items()}


# ============================================================
# Découpage en lots
# ============================================================

def chunked(it: Iterable[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    batch: List[Dict[str, Any]] = []
    for item in it:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


# ============================================================
# Index MongoDB
# ============================================================

def create_indexes(col) -> None:
    """
    Crée les index après import.

    Index simples (champs non-string typiques / filtrage fréquent) :
      - Age
      - Billing Amount
      - Room Number
      - Date of Admission
      - Discharge Date

    Index composé (utile pour vos contrôles de doublons et requêtes) :
      - (Name, Date of Admission)

    Remarque : on ne met PAS unique=True ici pour éviter l'échec si des doublons existent déjà.
    """
    col.create_index([("Age", ASCENDING)], name="idx_age")
    col.create_index([("Billing Amount", ASCENDING)], name="idx_billing_amount")
    col.create_index([("Room Number", ASCENDING)], name="idx_room_number")
    col.create_index([("Date of Admission", ASCENDING)], name="idx_date_of_admission")
    col.create_index([("Discharge Date", ASCENDING)], name="idx_discharge_date")

    # Accélère notamment les group-by / match sur ces deux champs
    col.create_index(
        [("Name", ASCENDING), ("Date of Admission", ASCENDING)],
        name="idx_name_date_of_admission",
    )


# ============================================================
# Programme principal
# ============================================================

def main() -> int:
    # Définition des arguments
    parser = argparse.ArgumentParser(description="Importer un CSV dans MongoDB.")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV")
    parser.add_argument("--mongo-uri", required=True, help="URI MongoDB")
    parser.add_argument("--db", required=True, help="Nom de la base MongoDB")
    parser.add_argument("--collection", required=True, help="Nom de la collection")
    parser.add_argument("--batch-size", type=int, default=1000, help="Taille des lots")

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Supprimer la collection avant import. Les index sont supprimés également.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Vider la collection sans la détruire (conserve les index). Ignoré si --drop est utilisé.",
    )
    parser.add_argument(
        "--skip-indexes",
        action="store_true",
        help="Ne pas créer d'index après import (utile pour importer plus vite, puis indexer plus tard). "
             "Ignoré si --drop n'est pas utilisé.",
    )

    args = parser.parse_args()

    # Test de la validité des arguments
    if args.batch_size <= 0:
        raise ValueError("--batch-size doit être strictement positif")

    # Identification de la base et de la collection
    client = MongoClient(args.mongo_uri)
    db = client[args.db]
    col = db[args.collection]

    # Vérification de la connexion (fail fast)
    client.admin.command("ping")

    # Suppression ou vidage de la collection existante
    if args.drop:
        col.drop()
        col = db[args.collection]  # récupère un handle propre
    elif args.clear:
        # Vidage des documents uniquement (index conservés)
        col.delete_many({})

    # Importation des données par batch
    rows = iter_csv_rows(args.csv)
    total_inserted = 0

    for batch in chunked(rows, args.batch_size):
        res = col.insert_many(batch, ordered=False)
        total_inserted += len(res.inserted_ids)

    # En cas de drop de la collection, création des index si demandé
    if args.drop and not args.skip_indexes:
        create_indexes(col)

    # Annonce de fin d'importation
    if args.drop:
        import_mode = "drop (collection recréée)"
    elif args.clear:
        import_mode = "clear (collection préalablement vidée)"
    else:
        import_mode = "append (documents ajoutés aux existants)"

    if args.drop and args.skip_indexes:
        index_status = "index supprimés"
    elif args.drop and not args.skip_indexes:
        index_status = "index créés"
    else:
        index_status = "index inchangés"

    print(
        f"Import terminé : {total_inserted} documents insérés dans "
        f"{args.db}.{args.collection} | "
        f"Mode d'importation={import_mode} | {index_status}."
    )
    return 0


# ============================================================
# Point d’entrée
# ============================================================

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrompu par l'utilisateur.", file=sys.stderr)
        raise SystemExit(130)
