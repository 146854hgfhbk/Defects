#!/usr/bin/env python3
"""Defects4X unified runner.

This is a thin, dependency-free orchestrator. It does not replace the language
toolchains; it resolves a case, fetches source, applies declared patches, and
prints the exact replay plan from the case JSON and oracle.

Usage:
    python scripts/d4x.py list --language dart
    python scripts/d4x.py show DART-101
    python scripts/d4x.py oracle DART-101
    python scripts/d4x.py fetch DART-101 --out /tmp/d4x
    python scripts/d4x.py patch DART-101 --work /tmp/d4x/DART-101
    python scripts/d4x.py plan DART-101
    python scripts/d4x.py verify
    python scripts/d4x.py verify --language swift
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
ORACLE = ROOT / "metadata" / "oracle.jsonl"
IDMAP = ROOT / "metadata" / "id-mapping.json"


def all_cases():
    return sorted(CASES.glob("*/*/case.json"))


def find_case(spec: str) -> Path:
    p = Path(spec)
    if p.is_file():
        return p
    if p.is_dir() and (p / "case.json").is_file():
        return p / "case.json"
    hits = list(CASES.glob(f"*/{spec}/case.json"))
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise SystemExit(f"ambiguous case: {spec}: {[str(h) for h in hits]}")
    raise SystemExit(f"case not found: {spec}")


def load_case(spec: str):
    p = find_case(spec)
    return p, json.loads(p.read_text(encoding="utf-8-sig"))


def load_oracle():
    rows = {}
    if ORACLE.is_file():
        for line in ORACLE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                rows[r["case_id"]] = r
    return rows


def guide_for(lang: str) -> str:
    return {
        "arkts": "env/device-arkts.md",
        "elixir": "env/container.md",
        "swift": "env/container.md",
    }.get(lang, f"env/{lang}.md")


def patch_files(case_dir: Path):
    out = []
    for d in (case_dir / "patches", case_dir / "trigger", case_dir / "evidence"):
        if d.is_dir():
            out.extend(sorted(d.glob("*.patch")))
    return out


def classify_patch(p: Path) -> str:
    n = p.name.lower()
    if "trigger" in n or "test" in n:
        return "trigger"
    if "source" in n or "production" in n or "fix" in n or "minimized" in n or n.endswith(".src.patch"):
        return "production"
    if "upstream" in n or "original" in n:
        return "upstream"
    return "other"


def select_patches(case_dir: Path, side: str):
    """Pick one trigger patch and, for fixed, one production patch.

    Packages often ship several equivalent patches (original/upstream/minimized).
    Applying all of them would fail or double-apply; use a deterministic priority.
    """
    files = patch_files(case_dir)
    trigger_pref = ["trigger-tests.patch", "trigger_test.patch", "test.patch",
                    "trigger.patch", "upstream-tests.patch"]
    prod_pref = ["minimized-source.patch", "minimized-production.patch",
                 "source.patch", "production-fix.patch", "minimized_fix.patch",
                 "minimized.patch", "production-source.patch"]
    def pick(pref):
        for name in pref:
            for q in files:
                if q.name == name:
                    return q
        for q in files:
            if classify_patch(q) in ("trigger" if "trigger" in pref[0] or "test" in pref[0] else ("production",)):
                return q
        return None
    chosen = []
    t = pick(trigger_pref)
    if t:
        chosen.append(t)
    if side == "fixed":
        p = pick(prod_pref)
        if p and p not in chosen:
            chosen.append(p)
    return chosen


def print_case(p: Path, c: dict, o: dict | None):
    lang = p.parent.parent.name
    print(f"case:      {c.get('case_id') or p.parent.name}")
    print(f"language:  {lang}")
    print(f"path:      {p.relative_to(ROOT)}")
    print(f"guide:     {guide_for(lang)}")
    print(f"oracle:    {(o or {}).get('oracle_level', 'MISSING')}")
    for k in ("project", "repository_url", "repo_url", "repository"):
        if c.get(k):
            print(f"{k}: {c[k]}")
            break
    for k in ("buggy_revision", "fixed_revision", "buggy_sha", "fixed_sha"):
        if c.get(k):
            print(f"{k}: {c[k]}")
    print("patches:")
    for q in patch_files(p.parent):
        print(f"  {q.relative_to(p.parent)}  [{classify_patch(q)}]")
    if o:
        print("expected:", json.dumps(o.get("expected"), ensure_ascii=False))
        print("trigger:", json.dumps(o.get("trigger"), ensure_ascii=False)[:300])


def cmd_list(args):
    rows = []
    for p in all_cases():
        lang = p.parent.parent.name
        if args.language and lang != args.language:
            continue
        c = json.loads(p.read_text(encoding="utf-8-sig"))
        rows.append({"case_id": p.parent.name, "language": lang,
                     "status": c.get("status") if isinstance(c.get("status"), str) else None})
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['language']:8} {r['case_id']:16} {r['status'] or ''}")
    print(f"count: {len(rows)}", file=sys.stderr)


def cmd_show(args):
    p, c = load_case(args.case)
    print_case(p, c, load_oracle().get(p.parent.name))


def cmd_oracle(args):
    p, c = load_case(args.case)
    o = load_oracle().get(p.parent.name)
    if not o:
        raise SystemExit(f"no oracle for {p.parent.name}")
    print(json.dumps(o, indent=2, ensure_ascii=False))


def cmd_fetch(args):
    p, c = load_case(args.case)
    cid = p.parent.name
    out = args.out or "/tmp/d4x-src"
    script = ROOT / "scripts" / "fetch_sources.py"
    r = subprocess.run([sys.executable, str(script), str(p), "--out", out], text=True)
    raise SystemExit(r.returncode)


def cmd_patch(args):
    p, c = load_case(args.case)
    work = Path(args.work)
    buggy = work / "buggy"
    fixed = work / "fixed"
    if not buggy.is_dir() or not fixed.is_dir():
        raise SystemExit(f"expected {buggy} and {fixed}; run: d4x fetch {p.parent.name} --out {work.parent}")
    side = args.side
    root = fixed if side == "fixed" else buggy
    selected = select_patches(p.parent, side)
    if not selected:
        print("no patches selected")
        return
    for q in selected:
        rel = q.relative_to(p.parent)
        rev = subprocess.run(["git", "-C", str(root), "apply", "--reverse", "--check", str(q)],
                             text=True, capture_output=True)
        if rev.returncode == 0:
            print(f"= already applied {rel}")
            continue
        print(f"+ git apply {rel}")
        chk = subprocess.run(["git", "-C", str(root), "apply", "--check", str(q)], text=True,
                             capture_output=True)
        if chk.returncode != 0:
            raise SystemExit(f"patch does not apply: {rel}\n{chk.stderr}")
        subprocess.run(["git", "-C", str(root), "apply", str(q)], check=True)
    print("applied", len(selected), "patches to", side)


def cmd_plan(args):
    p, c = load_case(args.case)
    cid = p.parent.name
    lang = p.parent.parent.name
    o = load_oracle().get(cid) or {}
    work = args.work or f"/tmp/d4x-work/{cid}"
    plan = {
        "case_id": cid,
        "language": lang,
        "guide": guide_for(lang),
        "steps": [
            f"python scripts/fetch_sources.py {cid} --out {work}",
            f"python scripts/d4x.py patch {cid} --work {work} --side buggy",
            f"python scripts/d4x.py patch {cid} --work {work} --side fixed",
            f"# install toolchain: {guide_for(lang)}",
            f"# run trigger: {json.dumps((o.get('trigger') or {}).get('command'))}",
            "# compare: buggy FAIL / fixed PASS",
        ],
        "expected": o.get("expected", {"buggy": "FAIL", "fixed": "PASS"}),
        "oracle_level": o.get("oracle_level", "MISSING"),
        "patches": {
            "buggy": [q.name for q in select_patches(p.parent, "buggy")],
            "fixed": [q.name for q in select_patches(p.parent, "fixed")],
        },
        "notes": o.get("notes"),
    }
    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        for s in plan["steps"]:
            print(s)
        print("expected:", plan["expected"], "oracle:", plan["oracle_level"])


def cmd_verify(args):
    errors = []
    case_files = all_cases()
    oracle = load_oracle()
    idmap = {}
    if IDMAP.is_file():
        idmap = {e["release_case_id"]: e for e in json.loads(IDMAP.read_text())["entries"]}
    for p in case_files:
        cid = p.parent.name
        lang = p.parent.parent.name
        if args.language and lang != args.language:
            continue
        try:
            c = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as e:
            errors.append(f"{cid}: invalid JSON: {e}")
            continue
        if not c.get("case_id") and not c.get("id") and not c.get("bug_id"):
            errors.append(f"{cid}: missing case id")
        if cid not in oracle:
            errors.append(f"{cid}: missing oracle")
        if lang == "swift" and cid not in idmap:
            errors.append(f"{cid}: missing Swift ID mapping")
        for q in p.parent.rglob("*"):
            if q.is_file() and q.stat().st_size > 100 * 1024 * 1024:
                errors.append(f"{cid}: file >100MB: {q}")
    n = len([p for p in case_files if not args.language or p.parent.parent.name == args.language])
    print(f"checked cases: {n}; errors: {len(errors)}")
    for e in errors[:50]:
        print("  -", e)
    return 0 if not errors else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list"); p.add_argument("--language"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_list)
    p = sub.add_parser("show"); p.add_argument("case"); p.set_defaults(func=cmd_show)
    p = sub.add_parser("oracle"); p.add_argument("case"); p.set_defaults(func=cmd_oracle)
    p = sub.add_parser("fetch"); p.add_argument("case"); p.add_argument("--out"); p.set_defaults(func=cmd_fetch)
    p = sub.add_parser("patch"); p.add_argument("case"); p.add_argument("--work", required=True); p.add_argument("--side", choices=["buggy", "fixed"], required=True); p.set_defaults(func=cmd_patch)
    p = sub.add_parser("plan"); p.add_argument("case"); p.add_argument("--work"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_plan)
    p = sub.add_parser("verify"); p.add_argument("--language"); p.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    rc = args.func(args)
    raise SystemExit(rc or 0)


if __name__ == "__main__":
    main()
