#!/usr/bin/env python3
"""integrity_checks_mongodb.py

Objectif
--------
Exécuter des tests d’intégrité sur une collection MongoDB afin de valider
la qualité des données après ingestion.

Ces contrôles sont conçus pour être :
- Automatisables (CI/CD, GitHub Actions)
- Non destructifs (lecture seule)
- Configurables (options CLI pour échouer ou non)

Types de contrôles
------------------
- Champs manquants ou nuls
- Conformité des types
- Détection de doublons
- Vérifications de cohérence

Utilisation typique
-------------------
python integrity_checks_mongodb.py \
  --mongo-uri mongodb://localhost:27017 \
  --db healthcare \
  --collection patients \
  --fail-on-missing --fail-on-type --fail-on-sanity
"""

import argparse
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple
from pymongo import MongoClient


# ============================================================
# Fonctions utilitaires
# ============================================================

def print_section(title: str) -> None:
    """Afficher un titre de section lisible dans la console.

    Utilisé pour structurer le rapport d’intégrité de manière claire
    et facilement lisible.
    """
    print("\n" + title)
    print("-" * len(title))


# ============================================================
# Analyse du schéma observé
# ============================================================

def observed_schema(col, sample_size: int = 1000) -> Dict[str, int]:
    """Observer les champs présents dans un échantillon de documents.

    Pourquoi un échantillon ?
    -------------------------
    - Performance : éviter un scan complet de la collection
    - Suffisant pour détecter les champs réellement utilisés

    Retour
    ------
    dict : {nom_du_champ: nombre_d_occurrences}
    """
    
    # Initilaliser la liste nom/nombre
    counts: Dict[str, int] = {}

    # Compter les occurences par noms de champ
    for doc in col.find({}, limit=sample_size):
        for k in doc.keys():
            counts[k] = counts.get(k, 0) + 1

    # Retourner le comptage
    return counts


# ============================================================
# Détection des valeurs manquantes
# ============================================================

def missing_values(col, expected_fields: Iterable[str]) -> List[str]:
    """Détecter les champs manquants ou nuls.

    Règle :
    -------
    Un champ est considéré manquant s’il est :
    - absent du document
    - présent mais égal à None

    Retour
    ------
    list : liste des champs problématiques
    """
    
    # Initialiser le compteur de champs manquants
    issues = []

    # Compter les champs manquants ou nuls
    for field in expected_fields:
        count = col.count_documents(
            {
                "$or": [
                    {field: {"$exists": False}},
                    {field: None},
                ]
            }
        )
        if count > 0:
            issues.append(field)

    # Retourner le comptage
    return issues


# ============================================================
# Vérification des types
# ============================================================

def type_checks(col, expected_types: Dict[str, Any]) -> List[Tuple[str, int]]:
    """Vérifier que les champs respectent les types attendus.

    Exemple :
    ---------
    - Age -> int
    - Billing Amount -> float
    - Date of Admission -> datetime

    Retour
    ------
    list de tuples : (champ, nombre_d_anomalies)
    """
    
   # Initialiser le compteur de types incorrects
    issues = []

    # Compter les erreurs de type
    for field, py_type in expected_types.items():
        count = col.count_documents(
            {
                field: {
                    "$exists": True,
                    "$ne": None,
                    "$not": {"$type": _mongo_type(py_type)},
                }
            }
        )
        if count > 0:
            issues.append((field, count))

    # Retourner le comptage
    return issues


def _mongo_type(py_type: Any) -> str:
    """Mapper un type Python vers un type MongoDB.

    Utilisé uniquement pour la vérification des types.
    """
    if py_type is int:
        return "int"
    if py_type is float:
        return "double"
    if py_type is datetime:
        return "date"
    return "string"


# ============================================================
# 5) Détection des doublons métier
# ============================================================

def duplicates(col) -> int:
    """Détecter les doublons selon une clé métier.

    Clé métier choisie :
    -------------------
    (Name, Date of Admission)

    Retour
    ------
    int : nombre de groupes de doublons détectés
    """
    
    # Grouper les documents par couples 'Name'/'Date of Admission' identiques,
    # compter le nombre de documents regroupés,
    # et ne retenir que les groupes de plus de 1 document
    pipeline = [
        {
            "$group": {
                "_id": {
                    "Name": "$Name",
                    "Date of Admission": "$Date of Admission",
                },
                "count": {"$sum": 1},
            }
        },
        {"$match": {"count": {"$gt": 1}}},
    ]

    # Retourner la liste des doublons
    return len(list(col.aggregate(pipeline)))


# ============================================================
# 6) Vérifications de cohérence métier (sanity checks)
# ============================================================

def sanity_checks(col) -> Dict[str, int]:
    """Appliquer des règles simples de cohérence métier.

    Règles de détection d'erreurs implémentées
    -------------------
    - Âge < 0 ou > 120
    - Montant de facturation négatif
    - Date de sortie antérieure à la date d’admission

    Retour
    ------
    dict : {nom_du_test: nombre_d_anomalies}
    """
    
    # Initialiser la liste du nombre d'incohérences par type
    results = {}

    # Compter les incohérences d'âge
    results["age_out_of_bounds"] = col.count_documents(
        {"Age": {"$exists": True, "$ne": None, "$not": {"$gte": 0, "$lte": 120}}}
    )

    # Compter les incohérences de facturation
    results["billing_negative"] = col.count_documents(
        {"Billing Amount": {"$exists": True, "$ne": None, "$lt": 0}}
    )

    # Compter les incohérences de dates
    results["discharge_before_admission"] = col.count_documents(
        {
            "Discharge Date": {"$exists": True, "$ne": None},
            "Date of Admission": {"$exists": True, "$ne": None},
            "$expr": {"$lt": ["$Discharge Date", "$Date of Admission"]},
        }
    )

    # Retourner le comptage d'incohérences
    return results


# ============================================================
# 7) Point d’entrée CLI
# ============================================================

def main() -> int:
    """Exécution principale des tests d’intégrité.

    Démarche globale
    ----------------
    1) Parser la ligne de commande (argparse)
    2) Connexion MongoDB
    3) Exécution des contrôles
    4) Affichage d’un rapport structuré
    5) Code de sortie selon la sévérité
    """
    
    # (1) Arguments CLI
    parser = argparse.ArgumentParser(description="Tests d’intégrité MongoDB")
    parser.add_argument("--mongo-uri", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--collection", required=True)

    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--fail-on-type", action="store_true")
    parser.add_argument("--fail-on-sanity", action="store_true")

    args = parser.parse_args()

    # (2) Connexion MongoDB
    client = MongoClient(args.mongo_uri)
    client.admin.command("ping")

    col = client[args.db][args.collection]

    # (3/4) Exécution des contrôles et rapport
    print("=" * 78)
    print("MongoDB – Rapport d’intégrité des données")
    print("=" * 78)

    print(f"Documents : {col.count_documents({})}")

    # Schéma observé
    print_section("Schéma observé")
    schema = observed_schema(col)
    print(f"Champs observés (échantillon) : {len(schema)}")

    # Champs attendus
    expected_fields = [
        "Name",
        "Age",
        "Billing Amount",
        "Date of Admission",
        "Discharge Date",
    ]

    # Valeurs manquantes
    print_section("Valeurs manquantes")
    missing = missing_values(col, expected_fields)
    if missing:
        print("Champs avec valeurs manquantes :", ", ".join(missing))
    else:
        print("Aucune valeur manquante détectée.")

    # Vérification des types
    print_section("Vérification des types")
    expected_types = {
        "Age": int,
        "Billing Amount": float,
        "Date of Admission": datetime,
        "Discharge Date": datetime,
    }
    type_issues = type_checks(col, expected_types)
    if type_issues:
        for field, count in type_issues:
            print(f"{field} : {count} anomalies de type")
    else:
        print("Aucune anomalie de type détectée.")

    # Doublons
    print_section("Doublons métier (Name + Date of Admission)")
    dup_count = duplicates(col)
    print(f"Groupes de doublons : {dup_count}")

    # Tests de cohérence 
    print_section("Vérifications de cohérence métier")
    sanity = sanity_checks(col)
    for k, v in sanity.items():
        print(f"{k} : {v}")

    # Code de sortie CI
    exit_code = 0
    if args.fail_on_missing and missing:
        exit_code = 1
    if args.fail_on_type and type_issues:
        exit_code = 1
    if args.fail_on_sanity and any(v > 0 for v in sanity.values()):
        exit_code = 1

    # Sortie avec code (0: ok, 1: erreur)
    return exit_code


# Lancement du main
if __name__ == "__main__":
    raise SystemExit(main())
