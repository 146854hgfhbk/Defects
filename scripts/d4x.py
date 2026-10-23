#!/usr/bin/env python3
"""Defects4X command-line interface.

A Defects4J-like CLI for the 850-case dataset:

    d4x info DART-101
    d4x checkout DART-101 --work /tmp/d4x
    d4x compile DART-101 --work /tmp/d4x --side buggy
    d4x test DART-101 --work /tmp/d4x --side buggy
    d4x run DART-101 --work /tmp/d4x
    d4x run DART-101 --work /tmp/d4x --dry-run

The runner is intentionally thin: it resolves the case, applies the declared
patches, runs the language command, and compares the outcome with the oracle.
It does not install toolchains or pull images; use env/ and prepare_images.py.
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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
    # Kotlin (and others) ship trigger-tests.patch at the case root; scanning
    # only the subdirectories silently skipped it, so the buggy side had no
    # failing test (KOTLIN-001: UNEXPECTED_PASS).
    out.extend(sorted(case_dir.glob("*.patch")))
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
    """Pick one trigger patch and, for fixed, one production patch."""
    files = patch_files(case_dir)
    trigger_pref = ["trigger-tests.patch", "trigger_test.patch", "test.patch",
                    "trigger.patch", "upstream-tests.patch"]
    prod_pref = ["minimized-source.patch", "minimized-production.patch",
                 "source.patch", "production-fix.patch", "minimized_fix.patch",
                 "minimized.patch", "production-source.patch"]

    def pick(pref, kind):
        for name in pref:
            for q in files:
                if q.name == name:
                    return q
        for q in files:
            if classify_patch(q) == kind:
                return q
        return None

    try:
        mode = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("revision_mode")
    except Exception:
        mode = None
    if mode == FIXED_MINUS_PATCH:
        # fixed side = fixed revision untouched; buggy side = fixed revision + patch
        if side == "fixed":
            return []
        p = pick(prod_pref, "production")
        return [p] if p else []

    chosen = []
    t = pick(trigger_pref, "trigger")
    if t:
        chosen.append(t)
    if side == "fixed":
        p = pick(prod_pref, "production")
        if p and p not in chosen:
            chosen.append(p)
    return chosen


def run_command(cmd, cwd: Path, timeout: int, log: Path):
    log.parent.mkdir(parents=True, exist_ok=True)
    if not cmd:
        return 127, "no command"
    shell = isinstance(cmd, str)
    printable = cmd if shell else " ".join(str(x) for x in cmd)
    with open(log, "w", encoding="utf-8") as f:
        f.write(f"$ {printable}\n\n")
        f.flush()
        try:
            p = subprocess.run(cmd, cwd=str(cwd), shell=shell, text=True,
                               stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            return p.returncode, printable
        except subprocess.TimeoutExpired:
            f.write(f"\nTIMEOUT after {timeout}s\n")
            return 124, printable
        except FileNotFoundError as e:
            f.write(f"\nNOT FOUND: {e}\n")
            return 127, printable


def compile_command(case: dict, lang: str):
    b = case.get("build") or {}
    if lang == "dart":
        dep = b.get("dependency_command") or ["dart", "pub", "get"]
        ana = b.get("analyze_command") or ["dart", "analyze"]
        fmt = lambda c: " ".join(shlex.quote(str(x)) for x in c)
        # Analyze only the package's own code. A bare `dart analyze` also scans
        # nested sub-packages (e.g. tool/*) whose deps were never resolved and
        # fails both sides with unrelated errors (DART-101: 19 errors in
        # tool/export_docs).
        if ana == ["dart", "analyze"]:
            return (f"{fmt(dep)} && dirs=$(ls -d lib bin test 2>/dev/null); "
                    f"dart analyze $dirs")
        return f"{fmt(dep)} && {fmt(ana)}"
    if lang == "julia":
        # No eager precompile: on some locked Manifests (JULIA-002 buggy) the
        # extension-precompile step errors with "failed to find source of parent
        # package" although the trigger itself runs fine. Precompilation happens
        # lazily on first `using`.
        return ("julia --project=. -e "
                "'using Pkg; Pkg.instantiate(; allow_autoprecomp=false)'")
    if lang == "kotlin":
        return b.get("build_command") or ("./gradlew " + b.get("compile_task", "")).strip()
    if lang == "lua":
        return None  # interpreted
    if lang == "perl":
        return (case.get("commands") or {}).get("build")
    if lang == "r":
        return "R CMD INSTALL ."
    if lang == "swift":
        return b.get("analyze_command") or ["swift", "build", "--build-tests"]
    if lang == "elixir":
        return "mix deps.get && mix compile"
    return None


def first_trigger_name(case: dict):
    t = case.get("triggering_test") or case.get("trigger_test")
    if isinstance(t, dict):
        return t.get("name") or t.get("path")
    if isinstance(t, str):
        return t
    ts = case.get("trigger_tests") or case.get("triggering_tests")
    if isinstance(ts, list) and ts:
        first = ts[0]
        if isinstance(first, dict):
            return first.get("name") or first.get("path")
        return str(first)
    return None


def test_command(case: dict, lang: str):
    b = case.get("build") or {}
    if lang == "dart":
        return b.get("test_command") or ["dart", "test", "--reporter=json"]
    if lang == "julia":
        tr = case.get("trigger") or {}
        if tr.get("path"):
            return f"julia --project=. {tr['path']}"
        return b.get("test_command")
    if lang == "kotlin":
        return b.get("test_command")
    if lang == "lua":
        sel = (case.get("manifest") or {}).get("trigger_selector") or {}
        return sel.get("command")
    if lang == "perl":
        return (case.get("commands") or {}).get("trigger_test")
    if lang == "r":
        # test_dir() alone does not attach the package under test, so every
        # test died with `could not find function ...` on both sides (BENCH-1).
        # Load the installed package (compile step ran R CMD INSTALL) and lift
        # testthat's default 10-failure cap so the full result is recorded.
        return ("Rscript -e 'pkg <- read.dcf(\"DESCRIPTION\")[1, \"Package\"]; "
                "testthat::set_max_fails(Inf); "
                "testthat::test_dir(\"tests/testthat\", package = pkg, "
                "load_package = \"installed\", stop_on_failure = TRUE)'")
    if lang == "swift":
        cmd = b.get("test_command") or ["swift", "test"]
        name = first_trigger_name(case)
        if isinstance(cmd, list) and name:
            cmd = cmd + ["--filter", str(name)]
        return cmd
    if lang == "elixir":
        return (case.get("commands") or {}).get("test")
    return None


def container_image(case: dict, lang: str):
    if lang == "swift":
        r = case.get("runtime_release") or {}
        if r.get("image_name"):
            return r["image_name"]
        img_id = r.get("image_id")
        if img_id:
            p = ROOT / "metadata" / "image-tags.json"
            if p.is_file():
                tags = json.loads(p.read_text(encoding="utf-8")).get("swift", {})
                if img_id in tags:
                    return tags[img_id]
            return img_id
    if lang == "elixir":
        return (case.get("environment") or {}).get("image")
    return None


def wrap_container(cmd, image: str, workdir: Path):
    if not image:
        raise SystemExit("container mode requires --image or a case image")
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(str(x)) for x in cmd)
    return ["docker", "run", "--rm", "--network", "none",
            "-v", f"{workdir}:/work", "-w", "/work", image,
            "bash", "-lc", cmd]


def side_dir(work: Path, case_id: str, side: str) -> Path:
    return work / case_id / side


FIXED_MINUS_PATCH = "fixed_minus_minimized_patch"


def case_rev(case: dict, side: str):
    # R cases: the buggy tree is the FIXED revision with the minimized source
    # patch applied (the patch re-introduces the bug). The parent commit has no
    # trigger test, so checking it out gives UNEXPECTED_PASS (BENCH-1).
    # Cases whose experiment fix tree is NOT the upstream fix commit
    # (artifacts.fixed.equals_upstream_tree == false): the production patch does
    # not apply to the upstream fix commit, so the fixed tree is built from the
    # base revision + trigger + production patch (SWIFT-D074, SWIFT-D095).
    if side == "fixed" and (((case.get("artifacts") or {}).get("fixed") or {})
                            .get("equals_upstream_tree") is False):
        side = "buggy"
    if side == "buggy" and case.get("revision_mode") == FIXED_MINUS_PATCH:
        side = "fixed"
    names = (("buggy_revision", "buggy_sha", "revision.id.buggy", "commits.buggy")
             if side == "buggy" else
             ("fixed_revision", "fixed_sha", "revision.id.fixed", "commits.fixed"))
    for name in names:
        if name in case and case[name]:
            return case[name]
        if "." in name:
            cur = case
            ok = True
            for part in name.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    ok = False
                    break
            if ok and cur:
                return cur
    return None


def fetch_side(case_path: Path, work: Path, side: str, force: bool):
    c = json.loads(case_path.read_text(encoding="utf-8-sig"))
    cid = case_path.parent.name
    out = work / cid
    repo = out / "repo.git"
    wt = out / side
    if force and wt.exists():
        if repo.exists():
            subprocess.run(["git", "--git-dir", str(repo), "worktree", "remove",
                            "--force", str(wt)], text=True, capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)
    if repo.exists():
        if not wt.exists():
            rev = case_rev(c, side)
            if not rev:
                raise SystemExit(f"{cid}: no {side} revision")
            r = subprocess.run(["git", "--git-dir", str(repo), "worktree", "add",
                                "--detach", str(wt), rev], text=True, capture_output=True)
            if r.returncode != 0:
                raise SystemExit(f"worktree add failed: {r.stderr}")
        return wt
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fetch_sources.py"),
                        str(case_path), "--out", str(work)], text=True)
    if r.returncode != 0:
        raise SystemExit(f"fetch failed for {cid}")
    return wt


def apply_patches(case_path: Path, side: str, wt: Path, force: bool):
    case_dir = case_path.parent
    if force:
        subprocess.run(["git", "-C", str(wt), "reset", "--hard"], text=True,
                       capture_output=True)
    applied = []
    for q in select_patches(case_dir, side):
        rev = subprocess.run(["git", "-C", str(wt), "apply", "--reverse", "--check", str(q)],
                             text=True, capture_output=True)
        if rev.returncode == 0:
            continue
        chk = subprocess.run(["git", "-C", str(wt), "apply", "--check", str(q)],
                             text=True, capture_output=True)
        if chk.returncode != 0:
            raise SystemExit(f"patch does not apply: {q.name}\n{chk.stderr}")
        subprocess.run(["git", "-C", str(wt), "apply", str(q)], check=True)
        applied.append(q.name)
    return applied


def cmd_info(args):
    p, c = load_case(args.case)
    lang = p.parent.parent.name
    o = load_oracle().get(p.parent.name, {})
    print(f"case:        {p.parent.name}")
    print(f"language:    {lang}")
    print(f"project:     {c.get('project') or c.get('repository_url') or c.get('repository')}")
    print(f"buggy:       {c.get('buggy_revision') or c.get('buggy_sha')}")
    print(f"fixed:       {c.get('fixed_revision') or c.get('fixed_sha')}")
    print(f"guide:       {guide_for(lang)}")
    print(f"oracle:      {o.get('oracle_level', 'MISSING')}")
    print(f"expected:    {json.dumps(o.get('expected', {}))}")
    print("patches:     " + ", ".join(f"{q.name} [{classify_patch(q)}]" for q in patch_files(p.parent)))
    print(f"trigger:     {json.dumps((o.get('trigger') or {}), ensure_ascii=False)[:400]}")


def cmd_bids(args):
    rows = []
    for p in all_cases():
        lang = p.parent.parent.name
        if args.language and lang != args.language:
            continue
        rows.append(p.parent.name)
    print("\n".join(rows))
    print(f"count: {len(rows)}", file=sys.stderr)


def cmd_query(args):
    for p in all_cases():
        lang = p.parent.parent.name
        c = json.loads(p.read_text(encoding="utf-8-sig"))
        status = c.get("status") if isinstance(c.get("status"), str) else None
        if args.language and lang != args.language:
            continue
        if args.status and status != args.status:
            continue
        print(f"{p.parent.name}\t{lang}\t{status or ''}")


def cmd_checkout(args):
    p, c = load_case(args.case)
    cid = p.parent.name
    work = Path(args.work).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    sides = [args.side] if args.side != "both" else ["buggy", "fixed"]
    for s in sides:
        wt = fetch_side(p, work, s, args.force)
        applied = apply_patches(p, s, wt, args.force)
        print(f"{cid} {s}: {wt}")
        if applied:
            print("  applied:", ", ".join(applied))


def stage_case_files(case_dir: Path, side: str, wt: Path):
    """Copy case-shipped files that live outside the upstream repo into the worktree.

    Julia cases ship a dedicated trigger script (trigger/trigger.jl) and per-side
    locked Project/Manifest (environment/<side>/). Without this the test command
    fails on both sides with "No such file" (JULIA-002).
    """
    import shutil as _sh
    for name in ("trigger.jl",):
        src = case_dir / "trigger" / name
        if src.is_file():
            (wt / "trigger").mkdir(exist_ok=True)
            _sh.copy2(src, wt / "trigger" / name)
    envd = case_dir / "environment" / side
    if envd.is_dir():
        for name in ("Project.toml", "Manifest.toml"):
            if (envd / name).is_file():
                _sh.copy2(envd / name, wt / name)


def elixir_verdict(side: str, log: Path, names: list):
    """Judge an Elixir run by trigger-test identity, not by the suite exit code.

    `mix test` exits non-zero if ANY test fails. Absinthe (ELIXIR-001) has 14
    baseline failures on both sides that are unrelated to the defect, so the
    raw exit code marks the fixed side UNEXPECTED_FAIL. Per the case's
    canonical_test_policy, the verdict must come from named trigger tests and
    a valid ExUnit summary.
    """
    import re as _re
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    m = _re.search(r"(\d+) tests?, (\d+) failures?", text)
    failed = [ln.strip() for ln in text.splitlines()
              if _re.match(r"\s*\d+\) test ", ln)]
    hit = [n for n in names if any(n in f for f in failed)]
    other = len(failed) - len(hit)
    if not m:
        return "BLOCKED", hit, other
    if side == "buggy":
        return ("FAIL_AS_EXPECTED" if hit else "UNEXPECTED_PASS"), hit, other
    return ("PASS" if not hit else "UNEXPECTED_FAIL"), hit, other


def swift_needs_test_discovery(root: Path) -> bool:
    """True when LinuxMain.swift is only a stub telling the user to pass
    --enable-test-discovery, or is an empty XCTMain. Without the flag
    `swift test` runs the stub and aborts on both sides (SWIFT-D080/D081)."""
    import re as _re
    for lm in (root / "Tests" / "LinuxMain.swift", root / "LinuxMain.swift"):
        if not lm.is_file():
            continue
        try:
            text = lm.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "swift test --enable-test-discovery" in text:
            return True
        if lm.parent == root and _re.search(r"XCTMain\(\s*\[\s*\]\s*\)", text):
            return True
    return False


def _run_side(args, p, c, side, work, lang, mode, image):
    cid = p.parent.name
    wt = fetch_side(p, work, side, args.force)
    applied = apply_patches(p, side, wt, args.force)
    logdir = work / cid / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    stage_case_files(p.parent, side, wt)
    timeout = args.timeout or 1800
    ccmd = compile_command(c, lang)
    tcmd = test_command(c, lang)
    if (lang == "swift" and isinstance(tcmd, list)
            and "--enable-test-discovery" not in tcmd
            and swift_needs_test_discovery(wt)):
        at = tcmd.index("test") + 1 if "test" in tcmd else len(tcmd)
        tcmd = tcmd[:at] + ["--enable-test-discovery"] + tcmd[at:]
    if mode == "container":
        img = image or container_image(c, lang)
        # Some Swift cases hard-code the toolchain at /opt/swiftNNN/usr/bin/swift
        # (the reference image layout). Rebuilt images ship swift at /usr/bin/swift,
        # so use the one on PATH instead (SWIFT-D070/D086/D089/D093/D097).
        if lang == "swift":
            import re as _re
            def _norm(cmd):
                pat = _re.compile(r"/opt/swift\d+/usr/bin/swift")
                if isinstance(cmd, list):
                    return [pat.sub("swift", x) if isinstance(x, str) else x for x in cmd]
                return pat.sub("swift", cmd) if isinstance(cmd, str) else cmd
            ccmd, tcmd = _norm(ccmd), _norm(tcmd)
        ccmd = wrap_container(ccmd, img, wt) if ccmd else None
        tcmd = wrap_container(tcmd, img, wt) if tcmd else None
    if args.dry_run:
        print(f"{side}: compile={ccmd}")
        print(f"{side}: test={tcmd}")
        return {"side": side, "compile_rc": None, "test_rc": None,
                "outcome": "DRY_RUN", "applied": applied}
    compile_rc = 0
    if ccmd:
        compile_rc, _ = run_command(ccmd, wt, timeout, logdir / f"{side}-compile.log")
        # Old SwiftPM packages whose LinuxMain.swift lists test cases that no longer
        # exist fail to build unless test discovery is on (SWIFT-D085). Retry once.
        if (compile_rc != 0 and lang == "swift"
                and ((wt / "Tests" / "LinuxMain.swift").is_file() or (wt / "LinuxMain.swift").is_file())
                and "--enable-test-discovery" not in str(ccmd)):
            retry = list(ccmd) if isinstance(ccmd, list) else ccmd
            if isinstance(retry, list):
                # ccmd is the docker wrapper: ["docker", ..., "bash", "-lc", "<cmd>"]
                retry[-1] = retry[-1] + " --enable-test-discovery"
                rc2, _ = run_command(retry, wt, timeout, logdir / f"{side}-compile-discovery.log")
                if rc2 == 0:
                    compile_rc = 0
                    if isinstance(tcmd, list) and tcmd and "--enable-test-discovery" not in str(tcmd):
                        tcmd = list(tcmd)
                        tcmd[-1] = tcmd[-1].replace("swift test", "swift test --enable-test-discovery", 1)
    if compile_rc != 0:
        return {"side": side, "compile_rc": compile_rc, "test_rc": None,
                "outcome": "COMPILE_ERROR", "applied": applied}
    if not tcmd:
        return {"side": side, "compile_rc": 0, "test_rc": None,
                "outcome": "BLOCKED", "applied": applied}
    test_rc, _ = run_command(tcmd, wt, timeout, logdir / f"{side}-test.log")
    extra = {}
    names = [n for n in (c.get("triggering_tests") or c.get("trigger_tests") or [])
             if isinstance(n, str)]
    if lang == "elixir" and names:
        outcome, hit, other = elixir_verdict(side, logdir / f"{side}-test.log", names)
        extra = {"trigger_failed": hit, "other_failures": other}
    elif side == "buggy":
        outcome = "FAIL_AS_EXPECTED" if test_rc != 0 else "UNEXPECTED_PASS"
    else:
        outcome = "PASS" if test_rc == 0 else "UNEXPECTED_FAIL"
    return {"side": side, "compile_rc": compile_rc, "test_rc": test_rc,
            "outcome": outcome, "applied": applied, **extra}


def cmd_run(args):
    p, c = load_case(args.case)
    cid = p.parent.name
    lang = p.parent.parent.name
    work = Path(args.work or f"/tmp/d4x-work/{cid}").expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    o = load_oracle().get(cid, {})
    mode = args.mode
    if mode == "auto":
        mode = "container" if lang in ("swift", "elixir") else "local"
    sides = ["buggy", "fixed"] if args.side == "both" else [args.side]
    results = {}
    for s in sides:
        results[s] = _run_side(args, p, c, s, work, lang, mode, args.image)
    result = {
        "schema_version": 1, "case_id": cid, "language": lang, "mode": mode,
        "oracle": o, "sides": results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if args.dry_run:
        return
    outcomes = {k: v.get("outcome") for k, v in results.items()}
    if any(o in ("COMPILE_ERROR", "BLOCKED") for o in outcomes.values()):
        verdict = "BLOCKED"
    elif (results.get("buggy", {}).get("outcome") == "FAIL_AS_EXPECTED"
          and results.get("fixed", {}).get("outcome") == "PASS"):
        verdict = "PASS"
    else:
        verdict = "FAIL"
    result["verdict"] = verdict
    (work / cid / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(outcomes, indent=2))
    print("VERDICT:", verdict)
    raise SystemExit(0 if verdict == "PASS" else (2 if verdict == "BLOCKED" else 1))


def cmd_compile(args):
    p, c = load_case(args.case)
    lang = p.parent.parent.name
    work = Path(args.work).expanduser().resolve()
    wt = side_dir(work, p.parent.name, args.side)
    ccmd = compile_command(c, lang)
    if args.mode == "container" and ccmd:
        ccmd = wrap_container(ccmd, args.image or container_image(c, lang), wt)
    if not ccmd:
        raise SystemExit("no compile command (interpreted language)")
    rc, _ = run_command(ccmd, wt, args.timeout, work / p.parent.name / "logs" / f"{args.side}-compile.log")
    print("compile rc", rc)
    raise SystemExit(rc)


def cmd_test(args):
    p, c = load_case(args.case)
    lang = p.parent.parent.name
    work = Path(args.work).expanduser().resolve()
    wt = side_dir(work, p.parent.name, args.side)
    tcmd = test_command(c, lang)
    if args.mode == "container" and tcmd:
        tcmd = wrap_container(tcmd, args.image or container_image(c, lang), wt)
    if not tcmd:
        raise SystemExit("no test command")
    rc, _ = run_command(tcmd, wt, args.timeout, work / p.parent.name / "logs" / f"{args.side}-test.log")
    print("test rc", rc)
    raise SystemExit(rc)


def cmd_export(args):
    p, c = load_case(args.case)
    o = load_oracle().get(p.parent.name, {})
    out = {"case": c, "oracle": o, "patches": [q.name for q in patch_files(p.parent)]}
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", args.out)


def cmd_plan(args):
    p, c = load_case(args.case)
    cid = p.parent.name
    lang = p.parent.parent.name
    o = load_oracle().get(cid) or {}
    work = args.work or f"/tmp/d4x-work/{cid}"
    plan = {
        "case_id": cid, "language": lang, "guide": guide_for(lang),
        "steps": [
            f"python scripts/d4x.py checkout {cid} --work {work}",
            f"python scripts/d4x.py compile {cid} --work {work} --side buggy",
            f"python scripts/d4x.py test {cid} --work {work} --side buggy",
            f"python scripts/d4x.py compile {cid} --work {work} --side fixed",
            f"python scripts/d4x.py test {cid} --work {work} --side fixed",
        ],
        "expected": o.get("expected", {"buggy": "FAIL", "fixed": "PASS"}),
        "oracle_level": o.get("oracle_level", "MISSING"),
        "patches": {"buggy": [q.name for q in select_patches(p.parent, "buggy")],
                    "fixed": [q.name for q in select_patches(p.parent, "fixed")]},
        "notes": o.get("notes"),
    }
    print(json.dumps(plan, indent=2, ensure_ascii=False) if args.json else "\n".join(plan["steps"]))


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
    ap = argparse.ArgumentParser(prog="d4x")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list"); p.add_argument("--language"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("bids"); p.add_argument("--language"); p.set_defaults(func=cmd_bids)
    p = sub.add_parser("query"); p.add_argument("--language"); p.add_argument("--status"); p.set_defaults(func=cmd_query)
    p = sub.add_parser("info"); p.add_argument("case"); p.set_defaults(func=cmd_info)
    p = sub.add_parser("show"); p.add_argument("case"); p.set_defaults(func=cmd_info)
    p = sub.add_parser("checkout"); p.add_argument("case"); p.add_argument("--work", default="/tmp/d4x-work"); p.add_argument("--side", choices=["buggy", "fixed", "both"], default="both"); p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_checkout)
    p = sub.add_parser("compile"); p.add_argument("case"); p.add_argument("--work", required=True); p.add_argument("--side", choices=["buggy", "fixed"], required=True); p.add_argument("--mode", choices=["local", "container"], default="local"); p.add_argument("--image"); p.add_argument("--timeout", type=int, default=1800); p.set_defaults(func=cmd_compile)
    p = sub.add_parser("test"); p.add_argument("case"); p.add_argument("--work", required=True); p.add_argument("--side", choices=["buggy", "fixed"], required=True); p.add_argument("--mode", choices=["local", "container"], default="local"); p.add_argument("--image"); p.add_argument("--timeout", type=int, default=1800); p.set_defaults(func=cmd_test)
    p = sub.add_parser("run"); p.add_argument("case"); p.add_argument("--work"); p.add_argument("--side", choices=["buggy", "fixed", "both"], default="both"); p.add_argument("--mode", choices=["auto", "local", "container"], default="auto"); p.add_argument("--image"); p.add_argument("--timeout", type=int, default=1800); p.add_argument("--force", action="store_true"); p.add_argument("--dry-run", action="store_true"); p.set_defaults(func=cmd_run)
    p = sub.add_parser("export"); p.add_argument("case"); p.add_argument("--out", required=True); p.set_defaults(func=cmd_export)
    p = sub.add_parser("oracle"); p.add_argument("case"); p.set_defaults(func=lambda a: print(json.dumps(load_oracle().get(load_case(a.case)[0].parent.name, {}), indent=2, ensure_ascii=False)))
    p = sub.add_parser("plan"); p.add_argument("case"); p.add_argument("--work"); p.add_argument("--json", action="store_true"); p.set_defaults(func=cmd_plan)
    p = sub.add_parser("verify"); p.add_argument("--language"); p.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    if args.cmd == "list":
        rows = []
        for q in all_cases():
            lang = q.parent.parent.name
            if args.language and lang != args.language:
                continue
            c = json.loads(q.read_text(encoding="utf-8-sig"))
            rows.append({"case_id": q.parent.name, "language": lang,
                         "status": c.get("status") if isinstance(c.get("status"), str) else None})
        print(json.dumps(rows, indent=2) if args.json else "\n".join(f"{r['language']:8} {r['case_id']:16} {r['status'] or ''}" for r in rows))
        print(f"count: {len(rows)}", file=sys.stderr)
        return
    rc = args.func(args)
    raise SystemExit(rc or 0)


if __name__ == "__main__":
    main()
