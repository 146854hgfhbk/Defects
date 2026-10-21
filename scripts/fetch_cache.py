#!/usr/bin/env python3
"""Fetch/prepare dependency caches listed in cache/index.json.

Usage:
    python scripts/fetch_cache.py DART-101
    python scripts/fetch_cache.py --language julia --all
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", nargs="?")
    ap.add_argument("--language")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--hf-base", default="https://huggingface.co/datasets/ManboOo/Defects4X/resolve/main")
    args = ap.parse_args()

    idx = json.loads((ROOT / "cache" / "index.json").read_text(encoding="utf-8"))
    cases = idx["cases"]
    if args.case:
        cases = [c for c in cases if c["case_id"] == args.case]
    elif args.language:
        cases = [c for c in cases if c["language"] == args.language]
    elif not args.all:
        ap.error("use CASE, --language, or --all")

    for c in cases:
        print(f"{c['case_id']}  {c['language']:8} {c.get('cache_type','-')}")
        art = c.get("artifact")
        if art:
            print(f"  download: {args.hf_base}/{art}")
        else:
            print(f"  recipe:   {c.get('source','see language guide')}")
    print(f"cases: {len(cases)}")


if __name__ == "__main__":
    main()
