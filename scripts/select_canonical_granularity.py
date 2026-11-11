#!/usr/bin/env python3
"""Select one Defects4J-style production patch per bug and project nested labels."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ACTIVE = ROOT / "metadata" / "active-bugs.csv"
CLASSIFIED = ROOT / "metadata" / "defects4j-granularity-classified.csv"
INDEX = ROOT / "metadata" / "defects4j-index.jsonl"
OUT = ROOT / "metadata"

SELECTION_ORDER = (
    ("canonical", "canonical_patch"),
    ("minimized", "minimized_patch"),
    ("upstream", "upstream_patch"),
)


def split_refs(value: str) -> list[str]:
    return [x.strip() for x in (value or "").replace("|", ";").split(";") if x.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def derive_labels(row: dict[str, str]) -> dict[str, object]:
    cls = row["classification"]
    audit = row.get("audit_status", "")
    outside = int(row.get("outside_changed_lines") or 0)
    functions = int(row.get("function_count") or 0)
    mapped = int(row.get("mapped_changed_lines") or 0)

    # Region scope takes precedence over the exact hunk label: any confirmed
    # outside production line makes the primary region OR, even when an older
    # variant row was assigned SH/SF by the patch-level mapper.
    if outside > 0:
        region = "OR"
        region_reason = "confirmed outside production lines"
        sl = sh = sf = False
    elif cls in {"SL", "SH", "SF"} and functions > 0 and mapped > 0:
        region = "SF"
        region_reason = "single-function mapping"
        sl = cls == "SL"
        sh = cls in {"SL", "SH"}
        sf = True
    elif cls == "MF" and functions > 1 and mapped > 0:
        region = "MF"
        region_reason = "multi-function mapping"
        sl = sh = sf = False
    elif cls == "UNCLASSIFIED" and audit == "CONFIRMED_FUNCTION_OUTSIDE":
        region = "OR"
        region_reason = "confirmed function-outside audit status"
        sl = sh = sf = False
    else:
        region = "UNRESOLVED"
        region_reason = "classification lacks reliable function mapping"
        sl = sh = sf = False

    return {
        "region_class": region,
        "region_reason": region_reason,
        "sl": sl,
        "sh": sh,
        "sf": sf,
        "mixed_function_outside": outside > 0 and functions > 0,
    }


def main() -> None:
    active_rows = read_csv(ACTIVE)
    class_rows = read_csv(CLASSIFIED)
    index_rows = [json.loads(line) for line in INDEX.read_text(encoding="utf-8").splitlines() if line.strip()]
    index_by_case = {r["case_id"]: r for r in index_rows}
    active_by_case = {r["bug_id"]: r for r in active_rows}
    variants_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in class_rows:
        variants_by_case[row["case_id"]].append(row)

    selected: list[dict[str, object]] = []
    errors: list[str] = []
    for bug_id in sorted(active_by_case):
        active = active_by_case[bug_id]
        index = index_by_case.get(bug_id, {})
        variants = variants_by_case.get(bug_id, [])
        by_key = {(r["patch_kind"], r["patch_path"]): r for r in variants}
        chosen = None
        chosen_kind = ""
        chosen_field = ""
        chosen_refs: list[str] = []
        for kind, field in SELECTION_ORDER:
            refs = split_refs(active.get(field, ""))
            for patch_path in refs:
                candidate = by_key.get((kind, patch_path))
                if candidate is not None:
                    chosen = candidate
                    chosen_kind = kind
                    chosen_field = field
                    chosen_refs = refs
                    break
            if chosen is not None:
                break
        if chosen is None:
            errors.append(f"{bug_id}: no audited row for canonical/minimized/upstream patch")
            continue

        projected = derive_labels(chosen)
        variant_labels = sorted({r["classification"] for r in variants})
        variant_regions = sorted({derive_labels(r)["region_class"] for r in variants})
        variant_paths = sorted({f"{r['patch_kind']}:{r['patch_path']}" for r in variants})
        row: dict[str, object] = {
            "bug_id": bug_id,
            "language": active.get("language") or index.get("language", ""),
            "project": active.get("project") or index.get("project", ""),
            "repository_url": active.get("repository_url") or index.get("repository_url", ""),
            "buggy_revision": active.get("buggy_revision") or index.get("buggy_revision", ""),
            "fixed_revision": active.get("fixed_revision") or index.get("fixed_revision", ""),
            "selected_patch_kind": chosen_kind,
            "selected_patch_field": chosen_field,
            "selected_patch_path": chosen["patch_path"],
            "selection_priority": ";".join(k for k, _ in SELECTION_ORDER),
            "selection_references": ";".join(chosen_refs),
            "classification": chosen["classification"],
            "reason": chosen["reason"],
            "audit_status": chosen["audit_status"],
            "changed_files": chosen["changed_files"],
            "changed_lines": int(chosen["changed_lines"] or 0),
            "hunk_count": int(chosen["hunk_count"] or 0),
            "function_count": int(chosen["function_count"] or 0),
            "functions": chosen["functions"],
            "mapped_changed_lines": int(chosen["mapped_changed_lines"] or 0),
            "outside_changed_lines": int(chosen["outside_changed_lines"] or 0),
            "outside_files": chosen["outside_files"],
            "outside_hunk_count": int(chosen["outside_hunk_count"] or 0),
            "variant_count": len(variants),
            "variant_labels": ";".join(variant_labels),
            "variant_region_classes": ";".join(variant_regions),
            "variant_exact_label_disagreement": len(set(variant_labels)) > 1,
            "variant_region_disagreement": len(set(variant_regions)) > 1,
            "variant_disagreement": len(set(variant_regions)) > 1,
            "variant_paths": ";".join(variant_paths),
            **projected,
        }
        selected.append(row)

    if errors:
        raise SystemExit("\n".join(errors))
    if len(selected) != len(active_rows) or len({r["bug_id"] for r in selected}) != len(selected):
        raise SystemExit(f"selection produced {len(selected)} rows for {len(active_rows)} active bugs")

    fields = list(selected[0])
    out_csv = OUT / "canonical-bugs-with-granularity.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(selected)

    summary: dict[str, object] = {
        "schema_version": 1,
        "unit": "bug",
        "bug_count": len(selected),
        "selection_order": [field for _, field in SELECTION_ORDER],
        "region_class_counts": dict(Counter(r["region_class"] for r in selected)),
        "nested_counts": {
            "SL": sum(bool(r["sl"]) for r in selected),
            "SH": sum(bool(r["sh"]) for r in selected),
            "SF": sum(bool(r["sf"]) for r in selected),
            "MF": sum(r["region_class"] == "MF" for r in selected),
            "OR": sum(r["region_class"] == "OR" for r in selected),
        },
        "selected_patch_kind_counts": dict(Counter(r["selected_patch_kind"] for r in selected)),
        "variant_region_disagreement_count": sum(bool(r["variant_region_disagreement"]) for r in selected),
        "variant_exact_label_disagreement_count": sum(bool(r["variant_exact_label_disagreement"]) for r in selected),
        "per_language": {},
        "definition": {
            "SL": "selected patch has exactly one changed production line; SL implies SH and SF",
            "SH": "selected patch has one function and one hunk with multiple changed production lines; SH implies SF",
            "SF": "selected patch has one function and multiple hunks, or an included SL/SH case",
            "MF": "selected patch changes multiple functions; disjoint from SF and OR",
            "OR": "selected patch has confirmed changed production lines outside function bodies; disjoint primary region class",
            "UNRESOLVED": "source/function mapping did not establish a reliable region class",
        },
        "notes": [
            "Canonical selection follows the one-row-per-bug active-bugs.csv patch references.",
            "Other minimized/upstream/canonical variants remain in variant_paths and variant_labels for audit.",
            "Nested counts overlap by design and must not be added to bug_count.",
        ],
    }
    by_lang: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in selected:
        by_lang[str(row["language"])].append(row)
    for lang, rows in sorted(by_lang.items()):
        summary["per_language"][lang] = {
            "bug_count": len(rows),
            "region_class_counts": dict(Counter(r["region_class"] for r in rows)),
            "nested_counts": {
                "SL": sum(bool(r["sl"]) for r in rows),
                "SH": sum(bool(r["sh"]) for r in rows),
                "SF": sum(bool(r["sf"]) for r in rows),
                "MF": sum(r["region_class"] == "MF" for r in rows),
                "OR": sum(r["region_class"] == "OR" for r in rows),
            },
        }
    (OUT / "canonical-granularity-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
