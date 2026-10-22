#!/usr/bin/env python3
"""Fetch upstream source for a Defects4X case at its pinned revisions.

Usage:
    python scripts/fetch_sources.py DART-101 --out /tmp/d4x-src
    python scripts/fetch_sources.py cases/dart/DART-101 --out /tmp/d4x-src
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_case(spec: str) -> Path:
    p = Path(spec)
    if p.is_file():
        return p
    if p.is_dir() and (p / "case.json").is_file():
        return p / "case.json"
    for cand in ROOT.glob(f"cases/*/{spec}/case.json"):
        return cand
    raise SystemExit(f"case not found: {spec}")


def deep_get(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return default
    return default if cur is None else cur


def get_field(case: dict, *names):
    """Read a field by literal key, dotted key, or nested path."""
    for name in names:
        if name in case and case[name]:
            return case[name]
        if "." in name:
            parts = name.split(".")
            cur = case
            ok = True
            for part in parts:
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok and cur:
                return cur
    return None


def repo_url(case: dict) -> str | None:
    v = get_field(case, "repository_url", "repo_url", "repository", "repo", "repository.url")
    if isinstance(v, str) and v:
        return v
    if isinstance(v, dict):
        for k in ("url", "html_url", "clone_url"):
            if v.get(k):
                return v[k]
    for path in (("repository", "url"), ("source", "repository"), ("source", "url")):
        v = deep_get(case, *path)
        if v:
            return v
    project = case.get("project")
    if isinstance(project, str) and "/" in project:
        return f"https://github.com/{project}.git"
    return None


def normalize_repo(url: str) -> str:
    url = url.strip()
    url = re.sub(r"/commit/.*$", "", url)
    url = re.sub(r"/pull/.*$", "", url)
    url = re.sub(r"/issues/.*$", "", url)
    url = re.sub(r"/tree/.*$", "", url)
    if url.startswith("git@"):
        url = "https://" + url[4:].replace(":", "/", 1)
    if not url.endswith(".git"):
        url += ".git"
    return url


def revisions(case: dict) -> tuple[str | None, str | None]:
    b = get_field(case, "buggy_revision", "buggy_sha", "revision.id.buggy",
                  "revision.buggy", "commits.buggy", "source.buggy_sha")
    f = get_field(case, "fixed_revision", "fixed_sha", "revision.id.fixed",
                  "revision.fixed", "commits.fixed", "source.fixed_sha",
                  "source_fix.fixed_revision")
    return b, f


def git(*args, cwd=None, check=True):
    proc = subprocess.run(["git", *args], cwd=cwd, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{proc.stdout}")
    return proc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--out", default="/tmp/d4x-src")
    ap.add_argument("--depth", type=int, default=0,
                    help="optional shallow depth; default keeps full history")
    args = ap.parse_args()

    case_path = find_case(args.case)
    case = json.loads(case_path.read_text(encoding="utf-8"))
    # Use the release directory name as the workdir ID. This matters for Swift,
    # where the release ID (SWIFT-Dxxx) differs from the package-internal ID.
    case_id = case_path.parent.name
    internal_id = case.get("case_id") or case.get("bug_id") or case.get("id")
    url = repo_url(case)
    buggy, fixed = revisions(case)
    if not url:
        raise SystemExit(f"{case_id}: no repository URL in {case_path}")
    if not buggy and not fixed:
        raise SystemExit(f"{case_id}: no buggy/fixed revisions in {case_path}")

    out = Path(args.out).expanduser().resolve() / str(case_id)
    out.mkdir(parents=True, exist_ok=True)

    repo = out / "repo.git"
    if not repo.exists():
        cmd = ["clone", "--bare", "--filter=blob:none", "--no-checkout", normalize_repo(url), str(repo)]
        if args.depth:
            cmd.insert(1, f"--depth={args.depth}")
        print("+", "git", " ".join(cmd))
        git(*cmd)
    else:
        print("using existing", repo)

    for side, rev in (("buggy", buggy), ("fixed", fixed)):
        if not rev:
            continue
        wt = out / side
        if wt.exists():
            print("exists", wt)
            continue
        print(f"+ worktree {side} {rev}")
        git("--git-dir", str(repo), "worktree", "add", "--detach", str(wt), rev)

    meta = {
        "case_id": case_id,
        "internal_case_id": internal_id,
        "repository": normalize_repo(url),
        "buggy_revision": buggy,
        "fixed_revision": fixed,
        "source_case": str(case_path),
        "out": str(out),
    }
    (out / "fetch.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
