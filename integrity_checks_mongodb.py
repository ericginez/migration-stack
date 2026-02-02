#!/usr/bin/env python3
r"""
Integrity checks for a MongoDB collection (Healthcare dataset).

Produces a human-readable console report and can export a JSON report.

Usage examples (PowerShell):
  python .\integrity_checks_mongodb_clean_report.py --db healthcare --collection patients
  python .\integrity_checks_mongodb_clean_report.py --db healthcare --collection patients --json integrity_report.json
  python .\integrity_checks_mongodb_clean_report.py --db healthcare --collection patients --show-types
  python .\integrity_checks_mongodb_clean_report.py --db healthcare --collection patients --fail-on-missing --fail-on-types --fail-on-duplicates --fail-on-sanity
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pymongo import MongoClient


DEFAULT_EXPECTED_FIELDS = [
    "Name","Age","Gender","Blood Type","Medical Condition",
    "Date of Admission","Doctor","Hospital","Insurance Provider",
    "Billing Amount","Room Number","Admission Type",
    "Discharge Date","Medication","Test Results"
]

DEFAULT_EXPECTED_TYPES: Dict[str, List[str]] = {
    "Name": ["string"],
    "Age": ["int", "long"],
    "Billing Amount": ["double", "decimal", "int", "long"],
    "Room Number": ["int", "long"],
    "Date of Admission": ["date"],
    "Discharge Date": ["date", "null"],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def count_documents(col) -> int:
    return col.count_documents({})


def sample_observed_fields(col, sample_size: int) -> List[str]:
    observed = set()
    cursor = col.find({}, projection={"_id": 0}).limit(sample_size)
    for d in cursor:
        observed |= set(d.keys())
    return sorted(observed)


def missing_values(col, fields: List[str]) -> Dict[str, Dict[str, int]]:
    stats: Dict[str, Dict[str, int]] = {}
    for f in fields:
        n_null = col.count_documents({f: None})
        n_absent = col.count_documents({f: {"$exists": False}})
        n_missing = col.count_documents({"$or": [{f: None}, {f: {"$exists": False}}]})
        stats[f] = {"missing_total": n_missing, "null": n_null, "absent": n_absent}
    return stats


def summarize_missing(missing_stats: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    return {k: v for k, v in missing_stats.items() if v["missing_total"] > 0}


def type_issues(col, expected_types: Dict[str, List[str]]) -> Dict[str, int]:
    issues: Dict[str, int] = {}
    for field, allowed in expected_types.items():
        q = {
            field: {"$exists": True, "$ne": None},
            "$expr": {"$not": [{"$in": [{"$type": f"${field}"}, allowed]}]},
        }
        n_bad = col.count_documents(q)
        if n_bad:
            issues[field] = n_bad
    return issues


def type_distributions(col, fields: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for field in fields:
        pipeline = [
            {"$match": {field: {"$exists": True}}},
            {"$project": {"t": {"$type": f"${field}"}}},
            {"$group": {"_id": "$t", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ]
        out[field] = list(col.aggregate(pipeline, allowDiskUse=True))
    return out


def duplicate_groups(col) -> List[Dict[str, Any]]:
    pipeline = [
        {"$group": {"_id": {"Name": "$Name", "Date of Admission": "$Date of Admission"}, "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$sort": {"count": -1}},
    ]
    return list(col.aggregate(pipeline, allowDiskUse=True))


def sanity_checks(col) -> Dict[str, int]:
    checks: Dict[str, int] = {}
    checks["age_out_of_bounds"] = col.count_documents({
        "Age": {"$exists": True, "$ne": None},
        "$or": [{"Age": {"$lt": 0}}, {"Age": {"$gt": 120}}],
    })
    checks["billing_negative"] = col.count_documents({
        "Billing Amount": {"$exists": True, "$ne": None, "$lt": 0}
    })
    checks["discharge_before_admission"] = col.count_documents({
        "Date of Admission": {"$type": "date"},
        "Discharge Date": {"$type": "date"},
        "$expr": {"$lt": ["$Discharge Date", "$Date of Admission"]},
    })
    return checks


def print_report(
    *,
    docs_count: int,
    observed_fields: List[str],
    expected_fields: List[str],
    missing_summary: Dict[str, Dict[str, int]],
    type_issue_counts: Dict[str, int],
    dup_groups_list: List[Dict[str, Any]],
    sanity: Dict[str, int],
    top_n_dups: int,
    show_types: bool,
    type_dists: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> None:
    print("=" * 78)
    print("MongoDB integrity report")
    print("=" * 78)
    print(f"Documents: {docs_count}")
    print()

    missing_in_sample = [f for f in expected_fields if f not in observed_fields]
    extra_in_sample = [f for f in observed_fields if f not in expected_fields]

    print("Schema (observed fields)")
    print("-" * 78)
    print(f"Observed (sample): {len(observed_fields)} fields")
    if missing_in_sample:
        print(f"Expected but NOT observed in sample: {missing_in_sample}")
    else:
        print("Expected fields all observed in sample.")
    if extra_in_sample:
        print(f"Extra observed fields (not in expected list): {extra_in_sample}")
    print()

    print("Missing values (null OR absent)")
    print("-" * 78)
    if not missing_summary:
        print("No missing values detected on expected fields.")
    else:
        for f, st in missing_summary.items():
            print(f"- {f}: missing_total={st['missing_total']} (null={st['null']}, absent={st['absent']})")
    print()

    print("Type checks")
    print("-" * 78)
    if not type_issue_counts:
        print("No type issues detected (for configured expected types).")
    else:
        for f, n in type_issue_counts.items():
            print(f"- {f}: {n} document(s) with unexpected type")
    print()

    if show_types and type_dists is not None:
        print("Type distributions ($type)")
        print("-" * 78)
        for f, dist in type_dists.items():
            if not dist:
                continue
            dist_str = ", ".join([f"{row['_id']}={row['count']}" for row in dist])
            print(f"- {f}: {dist_str}")
        print()

    print("Duplicates (Name + Date of Admission)")
    print("-" * 78)
    print(f"Duplicate groups: {len(dup_groups_list)}")
    if dup_groups_list:
        total_dup_docs = sum(g["count"] for g in dup_groups_list)
        print(f"Documents involved in duplicates: {total_dup_docs}")
        print(f"Top {top_n_dups} groups:")
        for g in dup_groups_list[:top_n_dups]:
            print(f"  {g['_id']} => {g['count']}")
    print()

    print("Sanity checks")
    print("-" * 78)
    for k, v in sanity.items():
        print(f"- {k}: {v}")
    print("=" * 78)


def compute_exit_code(
    *,
    missing_summary: Dict[str, Dict[str, int]],
    type_issue_counts: Dict[str, int],
    dup_groups_list: List[Dict[str, Any]],
    sanity: Dict[str, int],
    fail_on_duplicates: bool,
    fail_on_missing: bool,
    fail_on_types: bool,
    fail_on_sanity: bool,
) -> int:
    issues = 0
    if fail_on_missing and missing_summary:
        issues += 1
    if fail_on_types and type_issue_counts:
        issues += 1
    if fail_on_duplicates and dup_groups_list:
        issues += 1
    if fail_on_sanity and any(v > 0 for v in sanity.values()):
        issues += 1
    return 1 if issues else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MongoDB integrity checks (post-import).")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--db", required=True, help="Database name")
    parser.add_argument("--collection", required=True, help="Collection name")

    parser.add_argument("--sample-size", type=int, default=2000, help="Docs sampled for field discovery")
    parser.add_argument("--top-dups", type=int, default=10, help="Top N duplicate groups to print")
    parser.add_argument("--show-types", action="store_true", help="Print type distributions")
    parser.add_argument("--json", dest="json_path", default=None, help="Write full report to a JSON file")

    parser.add_argument("--fail-on-missing", action="store_true", help="Exit non-zero if missing values exist")
    parser.add_argument("--fail-on-types", action="store_true", help="Exit non-zero if type issues exist")
    parser.add_argument("--fail-on-duplicates", action="store_true", help="Exit non-zero if duplicates exist")
    parser.add_argument("--fail-on-sanity", action="store_true", help="Exit non-zero if any sanity check fails")

    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    col = client[args.db][args.collection]
    client.admin.command("ping")

    docs = count_documents(col)
    observed = sample_observed_fields(col, args.sample_size)

    miss = missing_values(col, DEFAULT_EXPECTED_FIELDS)
    miss_summary = summarize_missing(miss)

    t_issues = type_issues(col, DEFAULT_EXPECTED_TYPES)
    t_dists = type_distributions(col, list(DEFAULT_EXPECTED_TYPES.keys())) if args.show_types else None

    dups = duplicate_groups(col)
    sanity = sanity_checks(col)

    print_report(
        docs_count=docs,
        observed_fields=observed,
        expected_fields=DEFAULT_EXPECTED_FIELDS,
        missing_summary=miss_summary,
        type_issue_counts=t_issues,
        dup_groups_list=dups,
        sanity=sanity,
        top_n_dups=args.top_dups,
        show_types=args.show_types,
        type_dists=t_dists,
    )

    report = {
        "generated_at": _now_iso(),
        "mongo_uri": args.mongo_uri,
        "db": args.db,
        "collection": args.collection,
        "docs_count": docs,
        "sample_size": args.sample_size,
        "observed_fields": observed,
        "expected_fields": DEFAULT_EXPECTED_FIELDS,
        "missing_stats": miss,
        "type_issue_counts": t_issues,
        "duplicate_groups_count": len(dups),
        "duplicate_groups_top": dups[: args.top_dups],
        "sanity_checks": sanity,
    }

    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return compute_exit_code(
        missing_summary=miss_summary,
        type_issue_counts=t_issues,
        dup_groups_list=dups,
        sanity=sanity,
        fail_on_duplicates=args.fail_on_duplicates,
        fail_on_missing=args.fail_on_missing,
        fail_on_types=args.fail_on_types,
        fail_on_sanity=args.fail_on_sanity,
    )


if __name__ == "__main__":
    raise SystemExit(main())
