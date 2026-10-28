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
import os
import re
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


def declared_trigger_patch(case_dir: Path):
    """The trigger patch that case.json declares (patches.trigger_tests.path).

    Some cases ship several candidates (trigger-tests.patch, ...-compatible.patch,
    ...-stable.patch). Picking by file name applied the wrong one for 8 Swift cases;
    the declared one is the one the case was validated with.
    """
    try:
        c = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    pt = c.get("patches")
    if isinstance(pt, dict):
        tt = pt.get("trigger_tests")
        if isinstance(tt, dict) and isinstance(tt.get("path"), str):
            q = case_dir / tt["path"]
            if q.is_file():
                return q
    return None


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
    # case.json: artifacts.construction = "base + compatibility(if present) + trigger;
    # fixed adds production patch". The compatibility patch (patches.build_compatibility)
    # lets old sources build on the pinned toolchain (e.g. EVP_MD_type -> EVP_MD_get_type
    # for OpenSSL 3, SWIFT-D003); it goes on BOTH sides, before the trigger patch.
    try:
        _c = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
        _bc = ((_c.get("patches") or {}).get("build_compatibility") or {}).get("path")
        if isinstance(_bc, str) and (case_dir / _bc).is_file():
            chosen.append(case_dir / _bc)
    except Exception:
        pass
    t = declared_trigger_patch(case_dir) or pick(trigger_pref, "trigger")
    if t:
        chosen.append(t)
    if side == "fixed":
        p = pick(prod_pref, "production")
        # Opt-in D4X_KOTLIN_ORIGINAL_SOURCE=1: for Kotlin cases whose minimized-source.patch lost the
        # `import` lines the minimized code still uses (KOTLIN-133/144/146/149/150/151: fixed side
        # "Unresolved reference"), use the case's own patches/original-source.patch instead.
        # d4x-derived, not the dataset's declared fix patch: report such PASSes separately.
        if os.environ.get("D4X_KOTLIN_ORIGINAL_SOURCE") == "1" and case_dir.parent.name == "kotlin":
            _op = case_dir / "patches" / "original-source.patch"
            if _op.is_file():
                p = _op
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


def _kt_posix(cmd):
    """88 Kotlin cases declare Windows wrapper commands (`.\\gradlew.bat ...`); on Linux the
    same wrapper is `./gradlew`. Only the launcher spelling is changed, never the tasks."""
    if isinstance(cmd, str) and cmd.startswith(".\\gradlew.bat"):
        return "./gradlew" + cmd[len(".\\gradlew.bat"):]
    return cmd


def compile_command(case: dict, lang: str):
    b = case.get("build") or {}
    if lang == "dart":
        dep = b.get("dependency_command") or ["dart", "pub", "get"]
        ana = b.get("analyze_command") or ["dart", "analyze"]
        fmt = lambda c: " ".join(shlex.quote(str(x)) for x in c)
        if b.get("refresh_dependency_lock"):
            # Case-declared (build.refresh_dependency_lock_reason): the revision's
            # pubspec.lock pins a test chain that crashes the Dart 3.x test runner
            # ("Failed to load ..." for every file), so re-resolve from pubspec.yaml.
            _dep = "rm -f pubspec.lock && " + " ".join(shlex.quote(str(x)) for x in dep)
            fmt = lambda c, _d=_dep, _f=fmt: _d if c is dep else _f(c)
        # Analyze only the package's own code. A bare `dart analyze` also scans
        # nested sub-packages (e.g. tool/*) whose deps were never resolved and
        # fails both sides with unrelated errors (DART-101: 19 errors in
        # tool/export_docs).
        if ana == ["dart", "analyze"]:
            # `dart analyze` is fatal on warnings by default (Dart 2.19: DART-100 has
            # 3 non_nullable_equals_parameter warnings in test/ and failed both sides
            # at the compile gate). Only errors should block. SDKs before 2.10 have
            # no `dart pub` / `dart analyze`: fall back to `pub get` / `dartanalyzer`.
            return ("if dart pub --help >/dev/null 2>&1; then "
                    f"{fmt(dep)} && dirs=$(ls -d lib bin test 2>/dev/null); "
                    "rc=0; for d in $dirs; do dart analyze --no-fatal-warnings $d || rc=1; done; "
                    + ("true; " if os.environ.get("D4X_DART_ANALYZE_ADVISORY") == "1" else "[ $rc = 0 ]; ") +
                    "else pub get && dirs=$(ls -d lib bin test 2>/dev/null); "
                    "dartanalyzer --no-hints $dirs | tee /dev/stderr | "
                    "grep -qE '^ *error' && exit 1 || exit 0; fi")
        return f"{fmt(dep)} && {fmt(ana)}"
    if lang == "julia":
        # No eager precompile: on some locked Manifests (JULIA-002 buggy) the
        # extension-precompile step errors with "failed to find source of parent
        # package" although the trigger itself runs fine. Precompilation happens
        # lazily on first `using`.
        # Opt-in D4X_JULIA_PRECOMPILE=1: precompile in the compile step. JULIA-490's
        # trigger runs a child under `timeout 60s`; on a 2-core host the child's first
        # `using` spends most of that budget precompiling and gets KILLed (both sides).
        if os.environ.get("D4X_JULIA_PRECOMPILE") == "1":
            return ("julia --project=. -e "
                    "'using Pkg; Pkg.instantiate(; allow_autoprecomp=false); Pkg.precompile()'")
        return ("julia --project=. -e "
                "'using Pkg; Pkg.instantiate(; allow_autoprecomp=false)'")
    if lang == "kotlin":
        if b.get("android_sdk_required") and b.get("compile_task"):
            # Android modules have no `testClasses` task (KOTLIN-120..123: "task 'testClasses' not
            # found in project ':AnkiDroid'"); the case's own declared compile_task is the real one.
            return "./gradlew " + b["compile_task"]
        if os.environ.get("D4X_KOTLIN_DECLARED_TASKS") == "1" and b.get("compile_task"):
            return "./gradlew " + b["compile_task"]  # declared task, not a build_command naming another module
        return _kt_posix(b.get("build_command") or ("./gradlew " + b.get("compile_task", "")).strip())
    if lang == "lua":
        return None  # interpreted
    if lang == "perl":
        _b = (case.get("commands") or {}).get("build")
        # Opt-in D4X_PERL_DERIVE_BUILD=1: XS distributions (Text::CSV_XS ...) ship
        # build=null, so the trigger test would load an installed copy of the module
        # instead of the checkout (buggy side UNEXPECTED_PASS). Build in-tree, and
        # the test step then uses `prove -b`. d4x-derived, not dataset-declared.
        # Opt-in D4X_PERL_MAKE_ARGS: extra args for the declared `... && make`. Used for
        # Cpanel-JSON-XS, whose Makefile.PL adds -Werror and then trips over
        # declaration-after-statement inside Perl 5.38's own CORE/inline.h.
        # Dist::Zilla-only repos (PERL-097 Test-Deep: dist.ini, no Makefile.PL) cannot run
        # the declared `perl Makefile.PL && make`; with D4X_PERL_DERIVE_BUILD=1 skip the
        # build when neither Makefile.PL nor Build.PL exists (tests run from lib/).
        if _b and os.environ.get("D4X_PERL_DERIVE_BUILD") == "1" and "Makefile.PL" in _b:
            _b = f"if [ -f Makefile.PL ]; then {_b}; else true; fi"
        _ma = os.environ.get("D4X_PERL_MAKE_ARGS")
        if _b and _ma and "make" in _b:
            # Fallback only: a DEFINE= override REPLACES the Makefile's own DEFINE (and so
            # any -D feature macros Makefile.PL put there; PERL-243 then fails to build).
            # Try the declared build first, retry with the override only if it failed.
            return f"( {_b} ) || ( make clean >/dev/null 2>&1; {_b.replace('&& make', '&& make ' + _ma, 1)} )"
        if not _b and os.environ.get("D4X_PERL_DERIVE_BUILD") == "1":
            return ("if [ -f Makefile.PL ]; then perl Makefile.PL && make; "
                    "elif [ -f Build.PL ]; then perl Build.PL && ./Build; else true; fi")
        return _b
    if lang == "r":
        # Opt-in D4X_R_CASE_LIB=1: install the package under test into a per-case library
        # (.d4x-lib) instead of the shared R_LIBS tree. Installing every checkout into the
        # shared tree overwrote dependency versions later cases need (dplyr 1.0.0.9000 from
        # a DPLYR checkout broke DTPLYR-1: "namespace 'dplyr' 1.0.0.9000 is being loaded,
        # but >= 1.0.3 is required"; 34 R cases ended COMPILE_ERROR).
        if os.environ.get("D4X_R_CASE_LIB") == "1":
            return "mkdir -p .d4x-lib && R CMD INSTALL -l .d4x-lib ."
        return "R CMD INSTALL ."
    if lang == "swift":
        return b.get("analyze_command") or ["swift", "build", "--build-tests"]
    if lang == "elixir":
        # Opt-in D4X_ELIXIR_COMPILE_ENV=test: the test step runs in MIX_ENV=test, but
        # a default (dev) compile also builds `only: :dev` deps (ELIXIR-086: ex_doc ->
        # earmark 1.2.2 does not compile on Elixir 1.16) and fails both sides at the
        # compile gate for a dependency the tests never load.
        _e = os.environ.get("D4X_ELIXIR_COMPILE_ENV")
        if _e:
            return f"MIX_ENV={shlex.quote(_e)} mix deps.get && MIX_ENV={shlex.quote(_e)} mix compile"
        return "mix deps.get && mix compile"
    return None


def trigger_names(case: dict):
    """All distinct trigger test names of a case, in order.

    Swift cases can list several trigger tests; the defect may only show in a later
    one (SWIFT-D046: the first passes on the buggy side, the second fails). Filtering
    on the first name alone made such cases UNEXPECTED_PASS or under-tested.
    """
    out = []
    for key in ("triggering_tests", "trigger_tests", "triggering_test", "trigger_test"):
        v = case.get(key)
        items = v if isinstance(v, list) else ([v] if v else [])
        for x in items:
            n = x.get("name") if isinstance(x, dict) else x
            if isinstance(n, str) and n and n not in out:
                out.append(n)
        if out:
            break
    return out


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
        _tc = b.get("test_command") or ["dart", "test", "--reporter=json"]
        if _tc == ["dart", "test", "--reporter=json"]:
            # SDKs before 2.10 have no `dart test`; use `pub run test` there.
            # Some packages list `chrome` in dart_test.yaml platforms. Without a
            # browser every chrome suite fails to load on BOTH sides (fixed side then
            # shows UNEXPECTED_FAIL), so restrict to the VM platform when no Chrome
            # is installed. This narrows the run to VM-testable suites; recorded as a
            # deviation, not the case's declared command.
            # Cases whose reference run recorded null_safety_mode=legacy_unsound
            # (patches/minimization.json: `dart --no-sound-null-safety test`) cannot
            # load their suites under the default sound mode. Opt-in per run via
            # D4X_DART_UNSOUND=1 so cases already verified without it are untouched.
            _dt = "dart --no-sound-null-safety test" if os.environ.get("D4X_DART_UNSOUND") == "1" else "dart test"
            # Opt-in (D4X_DART_TRIGGER_FILES=1): run only the files that hold the
            # trigger tests. Used for suites where an unrelated test hangs for its
            # whole 12-minute timeout (DART-1148); the verdict is still judged by
            # trigger-test identity.
            _tf = ""
            if os.environ.get("D4X_DART_TRIGGER_FILES") == "1":
                _paths = sorted({e.get("path") for e in (case.get("triggering_tests") or case.get("trigger_tests") or [])
                                 if isinstance(e, dict) and e.get("path")})
                _tf = "".join(" " + shlex.quote(x) for x in _paths)
            return ["sh", "-c", "if dart pub --help >/dev/null 2>&1; then "
                    "if command -v google-chrome chromium chromium-browser >/dev/null 2>&1; "
                    f"then {_dt} --reporter=json{_tf}; "
                    f"else {_dt} -p vm --reporter=json{_tf}; fi; "
                    "else pub run test --reporter=json; fi"]
        return _tc
    if lang == "julia":
        tr = case.get("trigger") or {}
        if tr.get("path"):
            return f"julia --project=. {tr['path']}"
        return b.get("test_command")
    if lang == "kotlin":
        if b.get("android_sdk_required") and b.get("test_task"):
            return "./gradlew " + b["test_task"]  # declared test_task, not the aggregate `test`
        if os.environ.get("D4X_KOTLIN_DECLARED_TASKS") == "1" and b.get("test_task"):
            return "./gradlew " + b["test_task"]
        _kc = _kt_posix(b.get("test_command"))
        if os.environ.get("D4X_KOTLIN_CONTINUE") == "1" and isinstance(_kc, str) and "--continue" not in _kc:
            _kc += " --continue"  # run every module so trigger tests are not skipped by an earlier failure
        return _kc
    if lang == "lua":
        sel = (case.get("manifest") or {}).get("trigger_selector") or {}
        cmd = sel.get("command")
        # busted loads the system-installed Penlight (pl.*) itself before any spec
        # runs, so `require "pl.utils"` in a Penlight checkout silently resolved to
        # the installed library: the buggy side then PASSED (UNEXPECTED_PASS).
        # The helper drops the preloaded pl.* modules so the checkout is what is tested.
        if isinstance(cmd, list) and cmd and cmd[0] == "busted":
            helper = str(Path(__file__).resolve().parent / "lua_isolate.lua")
            cmd = [cmd[0], "--helper=" + helper] + cmd[1:]
            if os.environ.get("D4X_LUA_REFERENCE") == "1":
                # checkout-first, like the reference runner's Get-LuaPath: e.g. the argparse
                # repo's own specs must load ./src/argparse.lua, not an installed argparse
                cmd = ["env", "LUA_PATH=./lua/?.lua;./lua/?/init.lua;./src/?.lua;./src/?/init.lua;;"] + cmd
        elif isinstance(cmd, list) and cmd:
            # reference mode: a login shell (`sh -lc`) resets PATH and would drop the Lua 5.4
            # directory the batch put first; the reference image has `lua` = 5.4 anyway
            if os.environ.get("D4X_LUA_REFERENCE") == "1" and cmd[0] == "sh" and "-lc" in cmd:
                cmd = ["-c" if x == "-lc" else x for x in cmd]
            # Plain `lua tests/x.lua` / `sh -lc ...` triggers: same problem, the default
            # package.path misses the checkout's lua/ tree and falls back to the
            # system Penlight. Put the checkout first.
            cmd = ["env", "LUA_PATH=./lua/?.lua;./lua/?/init.lua;./src/?.lua;./src/?/init.lua;;"] + cmd
        return cmd
    if lang == "perl":
        _t = (case.get("commands") or {}).get("trigger_test")
        # Opt-in D4X_PERL_DERIVE_CMD=1: 33 cases ship commands.trigger_test=null but do
        # name trigger.test_file. Derive the same form the other 67 cases declare
        # (`prove -Ilib -It/lib <file>`). This command is d4x-derived, NOT declared by
        # the dataset; it is recorded as a deviation.
        if not _t and os.environ.get("D4X_PERL_DERIVE_CMD") == "1":
            _f = (case.get("trigger") or {}).get("test_file")
            if _f:
                # -b only when the in-tree build produced blib/; otherwise `prove -b`
                # silently falls back to a module installed on PERL5LIB and the checkout
                # is not what gets tested (PERL-097: buggy side UNEXPECTED_PASS).
                _bf = ' $([ -d blib ] && echo -b)' if os.environ.get("D4X_PERL_DERIVE_BUILD") == "1" else ""
                return f"prove{_bf} -Ilib -It/lib {shlex.quote(_f)}"
        return _t
    if lang == "r":
        if os.environ.get("D4X_R_TRIGGERS"):
            return "Rscript " + shlex.quote(str(Path(__file__).resolve().parent / "r_trigger_report.R"))
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
        names = trigger_names(case)
        if isinstance(cmd, list) and names:
            if any(n.startswith("compile::") for n in names):
                cmd = cmd + ["--filter", names[0]]   # compile diagnostics: one selector
            else:
                for n in names:                       # several --filter flags are OR-ed
                    cmd = cmd + ["--filter", n[:-2] if n.endswith("()") else n]
        return cmd
    if lang == "elixir":
        _tc = (case.get("commands") or {}).get("test")
        # Opt-in D4X_ELIXIR_SEED=<n>: append `--seed n` to the declared `mix test`. ExUnit shuffles
        # test order with a fresh seed on every run, and some Phoenix/Gettext suites depend on
        # order (ELIXIR-042: the same code passed with seeds 355350 and 361039 and failed with
        # 191303). Seed 0 turns shuffling off, so a run is repeatable. d4x-added, not declared
        # by the dataset: report results obtained this way as such.
        _sd = os.environ.get("D4X_ELIXIR_SEED")
        if isinstance(_tc, str) and _sd not in (None, "") and "--seed" not in _tc:
            _tc = _tc + f" --seed {int(_sd)}"
        # Opt-in D4X_ELIXIR_MAX_CASES=<n>: append `--max-cases n` to `mix test`. Phoenix integration suites bind a
        # fixed port per test and fail at random with :eaddrinuse when async modules overlap
        # (ELIXIR-051: a different WebSocketChannelsTest case failed in each of 6 runs). n=1 runs
        # modules one at a time. d4x-added, not declared by the dataset: report results as such.
        _mc = os.environ.get("D4X_ELIXIR_MAX_CASES")
        if isinstance(_tc, str) and _mc not in (None, "") and "--max-cases" not in _tc:
            _tc = _tc + f" --max-cases {int(_mc)}"
        return _tc
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


def wrap_container(cmd, image: str, workdir: Path, net: bool = False):
    if not image:
        raise SystemExit("container mode requires --image or a case image")
    if isinstance(cmd, list):
        cmd = " ".join(shlex.quote(str(x)) for x in cmd)
    if net:
        # Compile/dependency step only (opt-in D4X_CONTAINER_NET=1): `mix deps.get`
        # must reach hex.pm / github.com. Host network so the host proxy at
        # 127.0.0.1 is reachable. The TEST step always stays on --network none.
        px = os.environ.get("D4X_PROXY", "http://127.0.0.1:7890")
        return ["docker", "run", "--rm", "--network", "host",
                "-e", f"http_proxy={px}", "-e", f"https_proxy={px}",
                "-e", "no_proxy=localhost,127.0.0.1",
                "-v", f"{workdir}:/work", "-w", "/work", image,
                "bash", "-lc", cmd]
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
    # Kotlin (68 cases): revision_mode "base_plus_gold_patch" -- the dataset's fixed state is
    # the pinned base plus the production patch (environment.lock.json: "Synthetic fixed is the
    # pinned base plus the bound SWE-bench gold patch"); fixed_revision does not exist upstream.
    if side == "fixed" and case.get("revision_mode") == "base_plus_gold_patch":
        side = "buggy"
    if side == "buggy" and case.get("revision_mode") == FIXED_MINUS_PATCH:
        side = "fixed"
    # Lua: top-level revision.id.* disagree with manifest.*_sha in 53/100 cases
    # (and 39 name a different repository); the manifest triple is the consistent
    # one. Keep in sync with scripts/fetch_sources.py.
    _m = case.get("manifest") if isinstance(case.get("manifest"), dict) else {}
    if str(case.get("language")).lower() == "lua" and _m.get("repository"):
        _v = _m.get("buggy_sha" if side == "buggy" else "fixed_sha")
        if _v:
            return _v
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


def _reverse_buggy(case_dir: Path) -> bool:
    try:
        c = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    cons = c.get("construction")
    return isinstance(cons, dict) and cons.get("buggy_state") == "reverse_apply_canonical_minimized_patch"


def _added_lines_present(patch: Path, wt: Path) -> bool:
    """True if every '+' line of every file in the patch occurs in that file in wt."""
    cur, lines, ok, seen = None, None, True, False
    for ln in patch.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("+++ b/"):
            cur = wt / ln[6:]
            try:
                lines = set(cur.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                return False
        elif ln.startswith("+") and not ln.startswith("+++") and lines is not None:
            seen = True
            if ln[1:] not in lines:
                ok = False
    return ok and seen


def apply_patches(case_path: Path, side: str, wt: Path, force: bool):
    case_dir = case_path.parent
    if force:
        subprocess.run(["git", "-C", str(wt), "reset", "--hard"], text=True,
                       capture_output=True)
    applied = []
    # Opt-in D4X_LUA_REFERENCE=1: emulate the dataset's own targeted runner
    # (scripts/run_targeted_case.ps1 in the Lua package). It applies NO patch: fixed = the
    # fixed revision as-is; buggy = the buggy revision plus the regression test files copied
    # from the fixed revision. The patch-based emulation below fails on 6 cases whose
    # evidence patches do not belong to the case's revisions (EV-LU-070/115/155/165/167/170).
    if case_dir.parent.name == "lua" and os.environ.get("D4X_LUA_REFERENCE") == "1":
        if side == "buggy":
            import shutil as _sh3
            try:
                _rm = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("manifest") or {}
            except Exception:
                _rm = {}
            _fsha = _rm.get("fixed_sha")
            for _tf in [f.strip() for f in (_rm.get("regression_test_file") or "").split(";") if f.strip()]:
                # read the file at the fixed revision from the shared object store: the fixed
                # worktree does not exist yet when the buggy side is prepared first
                _gr = subprocess.run(["git", "-C", str(wt), "show", f"{_fsha}:{_tf}"], capture_output=True)
                if _fsha and _gr.returncode == 0:
                    (wt / _tf).parent.mkdir(parents=True, exist_ok=True)
                    (wt / _tf).write_bytes(_gr.stdout)
                    applied.append("overlay-from-fixed:" + _tf)
                else:
                    print(f"WARNING: LUA_REGRESSION_TEST_NOT_IN_FIXED {case_dir.name}: {_tf}")
        return applied
    # Lua: reproduction_mode "fixed-test-overlay-on-buggy". The buggy side is the
    # buggy revision plus the test-file hunks of the upstream fix commit; without
    # them the busted filter matches nothing and exits 0 (UNEXPECTED_PASS).
    # Several cases also ship an EMPTY upstream_trigger.patch, which git rejects.
    if case_dir.parent.name == "lua" and side == "buggy":
        try:
            _m = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("manifest") or {}
        except Exception:
            _m = {}
        _tf = [f for f in (_m.get("regression_test_file") or "").split(";") if f]
        _up = case_dir / "evidence" / "upstream.patch"
        if _tf and _up.is_file():
            _inc = ["--include=" + f for f in _tf]
            _r = subprocess.run(["git", "-C", str(wt), "apply", "--reverse", "--check", *_inc, str(_up)],
                                text=True, capture_output=True)
            if _r.returncode != 0:
                _c = subprocess.run(["git", "-C", str(wt), "apply", "--check", *_inc, str(_up)],
                                    text=True, capture_output=True)
                if _c.returncode != 0:
                    # evidence/upstream.patch does not belong to this case's revisions
                    # (19 Lua cases: commit.txt fixed_sha != case fixed revision).
                    print(f"WARNING: LUA_OVERLAY_SKIPPED {case_dir.name}: {_c.stderr.strip()}")
                else:
                    subprocess.run(["git", "-C", str(wt), "apply", *_inc, str(_up)], check=True)
                    applied.append("upstream.patch[tests-only]")
    _lua_tf = []
    if case_dir.parent.name == "lua":
        try:
            _lm = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("manifest") or {}
        except Exception:
            _lm = {}
        _lua_tf = [f for f in (_lm.get("regression_test_file") or "").split(";") if f]
    _jl_dedicated = False
    if case_dir.parent.name == "julia":
        try:
            _jl_dedicated = ((json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
                              .get("trigger") or {}).get("mode") == "dedicated_script")
        except Exception:
            _jl_dedicated = False
    for q in select_patches(case_dir, side):
        if q.stat().st_size == 0:
            continue
        if _jl_dedicated and q.name == "upstream-tests.patch":
            # Julia cases whose trigger.mode is "dedicated_script" run trigger/trigger.jl.
            # trigger/upstream-tests.patch is the superseded pre-dedicated artifact
            # (JULIA-384/706: does not apply to the buggy revision); do not apply it.
            print(f"WARNING: JULIA_STALE_UPSTREAM_TESTS_SKIPPED {case_dir.name}")
            continue
        if _lua_tf and q.name == "upstream_trigger.patch":
            # Stale artifact in part of the Lua cases: it patches test files of a
            # different project than manifest.regression_test_file. The tests-only
            # overlay from evidence/upstream.patch (above) already supplies the test.
            import re as _re2
            _touched = _re2.findall(r"^diff --git a/(\S+)", q.read_text(encoding="utf-8", errors="replace"), _re2.M)
            if not any(t in _touched for t in _lua_tf):
                print(f"WARNING: LUA_STALE_TRIGGER_PATCH_SKIPPED {case_dir.name}: touches {_touched[:2]}")
                continue
        # Julia (47 cases): construction.buggy_state is
        # "reverse_apply_canonical_minimized_patch": the patch is the FIX, and the
        # buggy tree is the fixed commit with it reverse-applied. The generic
        # "already applied" shortcut below would skip it and leave buggy == fixed
        # (UNEXPECTED_PASS on the buggy side).
        if side == "buggy" and _reverse_buggy(case_dir):
            _rv = subprocess.run(["git", "-C", str(wt), "apply", "--reverse", "--check", str(q)],
                                 text=True, capture_output=True)
            if _rv.returncode != 0:
                raise SystemExit(f"patch does not reverse-apply: {q.name}\n{_rv.stderr}")
            subprocess.run(["git", "-C", str(wt), "apply", "--reverse", str(q)], check=True)
            applied.append(q.name + "[reversed]")
            continue
        # R (all 100 cases): revision_mode "fixed_minus_minimized_patch". The buggy tree is the
        # FIXED revision with the minimized source patch applied FORWARD (the patch deletes
        # the fix). The generic "already applied" shortcut below tests `apply --reverse
        # --check`, which passes spuriously for a pure-deletion patch (git only has to find
        # the context lines), so it skipped the patch and left buggy == fixed (CLOCK-1:
        # UNEXPECTED_PASS). For R, try the forward apply first.
        if side == "buggy" and case_dir.parent.name == "r":
            try:
                _rmode = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("revision_mode")
            except Exception:
                _rmode = None
            if _rmode == FIXED_MINUS_PATCH:
                _fw = subprocess.run(["git", "-C", str(wt), "apply", "--check", str(q)],
                                     text=True, capture_output=True)
                if _fw.returncode == 0:
                    subprocess.run(["git", "-C", str(wt), "apply", str(q)], check=True)
                    applied.append(q.name)
                    continue
        rev = subprocess.run(["git", "-C", str(wt), "apply", "--reverse", "--check", str(q)],
                             text=True, capture_output=True)
        if rev.returncode == 0:
            continue
        chk = subprocess.run(["git", "-C", str(wt), "apply", "--check", str(q)],
                             text=True, capture_output=True)
        if chk.returncode != 0 and b"\r\n" in q.read_bytes():
            # Patch shipped with CRLF line endings (7 Kotlin trigger patches, case.json
            # line_endings_normalized_for_git) while the checkout is LF: normalise the patch only.
            import tempfile as _tf2
            _nb = q.read_bytes().replace(b"\r\n", b"\n")
            with _tf2.NamedTemporaryFile("wb", suffix=".patch", delete=False) as _t2:
                _t2.write(_nb)
            _rk = subprocess.run(["git", "-C", str(wt), "apply", "--reverse", "--check", _t2.name],
                                 text=True, capture_output=True)
            if _rk.returncode == 0:
                # trigger tests already present in this revision (fixed side of real_upstream_commit)
                print(f"WARNING: PATCH_CRLF_ALREADY_APPLIED {case_dir.name}: {q.name}")
                continue
            _ck = subprocess.run(["git", "-C", str(wt), "apply", "--check", _t2.name],
                                 text=True, capture_output=True)
            if _ck.returncode == 0:
                subprocess.run(["git", "-C", str(wt), "apply", _t2.name], check=True)
                applied.append(q.name + "[crlf-normalized]")
                print(f"WARNING: PATCH_CRLF_NORMALIZED {case_dir.name}: {q.name}")
                continue
        if chk.returncode != 0:
            # Fixed side only: a trigger-test patch carved out of the fix commit may
            # be neither forward- nor reverse-applicable because the fixed revision
            # carries additional unrelated edits to the same test files (DART-1120).
            # Accept it as already present only if EVERY added line is found in the
            # target file; otherwise keep failing.
            if side == "fixed" and _added_lines_present(q, wt):
                print(f"WARNING: PATCH_ALREADY_PRESENT_BY_CONTENT {case_dir.name}: {q.name}")
                continue
            raise SystemExit(f"patch does not apply: {q.name}\n{chk.stderr}")
        subprocess.run(["git", "-C", str(wt), "apply", str(q)], check=True)
        applied.append(q.name)
    # Kotlin, opt-in (D4X_KOTLIN_RETAIN_API=1): the trigger tests of a few cases call API that the
    # fix introduces (KOTLIN-189 hasModifier, KOTLIN-194 lineLength), so the buggy tree cannot
    # compile them. patches/buggy-retained-api.json lists files whose diff from the fix is
    # purely additive declarations; that file-level diff is forward-applied to the buggy side only.
    if (side == "buggy" and case_dir.parent.name == "kotlin"
            and os.environ.get("D4X_KOTLIN_RETAIN_API") == "1"
            and (case_dir / "patches" / "buggy-retained-api.json").is_file()):
        _spec = json.loads((case_dir / "patches" / "buggy-retained-api.json").read_text(encoding="utf-8"))
        _src = case_dir / "patches" / _spec.get("source_patch", "original-source.patch")
        _txt = _src.read_text(encoding="utf-8", errors="replace")
        _parts = re.split(r"(?m)^(?=diff --git )", _txt)
        _keep = [x for x in _parts if any(x.startswith(f"diff --git a/{f} ") for f in _spec["files"])]
        if len(_keep) != len(_spec["files"]):
            raise SystemExit(f"retained-api files not found in {_src.name}")
        import tempfile as _tf3
        with _tf3.NamedTemporaryFile("w", suffix=".patch", delete=False, encoding="utf-8", newline="\n") as _t3:
            _t3.write("".join(_keep))
        subprocess.run(["git", "-C", str(wt), "apply", "--check", _t3.name], check=True)
        subprocess.run(["git", "-C", str(wt), "apply", _t3.name], check=True)
        applied.append("buggy-retained-api:" + ",".join(Path(f).name for f in _spec["files"]))
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
    _names = ["trigger.jl"]
    # JULIA-055 ships its dedicated script under another name
    # (trigger/JULIA-055-splitfunction.jl); case.json trigger.path says which.
    try:
        _tp = (json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig")).get("trigger") or {}).get("path")
        if isinstance(_tp, str) and _tp.startswith("trigger/") and Path(_tp).name not in _names:
            _names.append(Path(_tp).name)
    except Exception:
        pass
    for name in _names:
        src = case_dir / "trigger" / name
        if src.is_file():
            (wt / "trigger").mkdir(exist_ok=True)
            _sh.copy2(src, wt / "trigger" / name)
    # Lua curator triggers (`lua evidence/d4j_trigger.lua`): the script lives in the case
    # dir, not in the upstream repo, so it has to be staged into the worktree. Without it
    # both sides die with "cannot open evidence/d4j_trigger.lua" and the buggy side's FAIL
    # is a false positive.
    if case_dir.parent.name == "lua":
        _lt = case_dir / "evidence" / "d4j_trigger.lua"
        if _lt.is_file():
            (wt / "evidence").mkdir(exist_ok=True)
            _sh.copy2(_lt, wt / "evidence" / "d4j_trigger.lua")
    envd = case_dir / "environment" / side
    # Dart: cases ship the lock the reference run resolved. Opt-in only
    # (D4X_STAGE_DART_LOCK=1) because the default path re-resolves from
    # pubspec.yaml and that is what the already-passing cases were verified with.
    if case_dir.parent.name == "dart" and os.environ.get("D4X_STAGE_DART_LOCK") == "1":
        for pre in ("post-minimization-", "original-"):
            lk = case_dir / "environment" / f"{pre}{side}-pubspec.lock"
            if lk.is_file():
                _sh.copy2(lk, wt / "pubspec.lock")
                print(f"NOTE: DART_LOCK_STAGED {case_dir.name}: {lk.name}")
                break
    if envd.is_dir():
        for name in ("Project.toml", "Manifest.toml"):
            if (envd / name).is_file():
                _sh.copy2(envd / name, wt / name)


def elixir_failed_names(log: Path):
    """Names of failed ExUnit tests/doctests in a `mix test` log."""
    import re as _re
    if not log.is_file():
        return []
    out = []
    for ln in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _re.match(r"\s*\d+\) (test|doctest) (.*)$", ln)
        if m:
            out.append(m.group(2).strip() if m.group(1) == "test" else (m.group(1) + " " + m.group(2).strip()))
    return out


def elixir_unlisted_failures(log: Path, excluded_path: Path):
    """Return (checked, unlisted). `checked` is False when the case ships no
    validation/excluded-tests.json, in which case nothing can be verified."""
    if not excluded_path.is_file():
        return False, []
    d = json.loads(excluded_path.read_text(encoding="utf-8"))
    allowed = set()
    for e in d.get("excluded_tests", []):
        t = e.get("test") if isinstance(e, dict) else e
        if isinstance(t, str):
            allowed.add(t.strip())
            allowed.add(t.strip()[5:] if t.strip().startswith("test ") else t.strip())
    return True, [n for n in elixir_failed_names(log) if n not in allowed]


def _kt_norm_test(name):
    # Gradle prints either "pkg.Class > test" or "Class > test"; compare on the simple class name.
    return re.sub(r"^(?:[\w$]+\.)+(?=[\w$]+ > )", "", name.strip())


def kotlin_failed_tests(log):
    """(names, reported): tests printed as '<test> FAILED' in a Gradle log, and the count from
    the 'N tests completed, M failed' summary line (None if absent)."""
    names, reported = [], None
    if not log.is_file():
        return names, reported
    for ln in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\S.* > .*\S) FAILED\s*$", ln)
        if m and not ln.startswith("> Task"):
            names.append(_kt_norm_test(m.group(1)))
        m = re.search(r"(\d+) tests completed, (\d+) failed", ln)
        if m:
            reported = (reported or 0) + int(m.group(2))
    return names, reported


def kotlin_excluded_verdict(log, excluded_path, trig_classes=()):
    """Fixed side with a non-zero Gradle exit: OK only if every failed test is listed in
    validation/excluded-tests.json and the parsed failures account for the reported count."""
    d = json.loads(excluded_path.read_text(encoding="utf-8"))
    allowed = set()
    for e in d.get("excluded_tests", []):
        t = e.get("test") if isinstance(e, dict) else e
        if isinstance(t, str):
            allowed.add(_kt_norm_test(t))
    names, reported = kotlin_failed_tests(log)
    unlisted = [n for n in names if n not in allowed]
    ok = bool(names) and not unlisted and reported == len(names)
    if ok and trig_classes:
        text = log.read_text(encoding="utf-8", errors="replace")
        for cls in trig_classes:
            if not re.search(r"(?m)^(?:[\w$.]+\.)?" + re.escape(cls) + r" > .* PASSED\s*$", text):
                ok = False
                unlisted.append("TRIGGER NOT SEEN PASSED: " + cls)
    return ok, names, unlisted


def dart_verdict(side: str, log: Path, trig: list):
    """Judge a Dart run by trigger-test identity (dart test --reporter=json), not
    by the suite exit code. Unrelated baseline failures (formatter-version drift,
    network, missing tools) otherwise turn the fixed side UNEXPECTED_FAIL.
    buggy: at least one trigger test must really fail (or its file fail to load).
    fixed: every trigger test must be seen and pass."""
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    names, suite_of, suites, failed, passed = {}, {}, {}, set(), set()
    for ln in text.splitlines():
        if not ln.startswith("{"):
            continue
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        if j.get("suite"):
            suites[j["suite"]["id"]] = j["suite"].get("path") or ""
        t = j.get("test")
        if t:
            names[t["id"]] = t.get("name", "")
            suite_of[t["id"]] = t.get("suiteID")
        if j.get("type") == "testDone" and not j.get("skipped"):
            (passed if j.get("result") == "success" else failed).add(j["testID"])
    seen = set()
    hit, ok = [], []
    for e in trig:
        nm, path = e.get("name", ""), e.get("path", "")
        key = (path, nm)
        if key in seen or not nm:
            continue
        seen.add(key)
        # Match by the suite (test file) that owns the test, not the test's source
        # url: table-driven suites (dart_style formatter_test) generate their tests
        # from test/utils.dart, so url points at the helper, not the test file.
        ids = [i for i, n in names.items()
               if nm in n and (not path or suites.get(suite_of.get(i), "").endswith(path))]
        load_failed = any(path and path in names[i] and names[i].startswith("loading ")
                          for i in failed)
        if any(i in failed for i in ids) or load_failed:
            hit.append(nm)
        elif any(i in passed for i in ids):
            ok.append(nm)
    other = len([i for i in failed if not names.get(i, "").startswith("loading ")]) - len(hit)
    if not hit and not ok:
        return "BLOCKED", hit, max(other, 0)
    if side == "buggy":
        if hit:
            return "FAIL_AS_EXPECTED", hit, max(other, 0)
        return ("UNEXPECTED_PASS" if len(ok) == len(seen) else "BLOCKED"), hit, max(other, 0)
    if hit:
        return "UNEXPECTED_FAIL", hit, max(other, 0)
    return ("PASS" if len(ok) == len(seen) else "BLOCKED"), hit, max(other, 0)


def r_verdict(side: str, log: Path, trig: list):
    """Judge an R run by trigger-test identity (D4X_TEST lines from r_trigger_report.R).

    A trigger name is `file :: test` or `file :: context / test`; both spellings are
    indexed. buggy: at least one trigger test must fail. fixed: every trigger test must
    have run and passed (a skipped or never-seen trigger test is BLOCKED, never PASS)."""
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    rank = {"ok": 0, "skip": 1, "fail": 2}
    rows = {}

    def put(k, st):
        k = " ".join(k.split())
        if rank.get(st, 0) >= rank.get(rows.get(k, "ok"), 0):
            rows[k] = st

    n_tests = 0
    for ln in text.splitlines():
        if not ln.startswith("D4X_TEST\t"):
            continue
        parts = ln.split("\t")
        if len(parts) >= 5:
            f, cx, t, st = parts[1], parts[2], parts[3], parts[4].strip()
        elif len(parts) >= 3:
            f, cx, t, st = "", "", parts[1], parts[2].strip()
        else:
            continue
        n_tests += 1
        put(f"{f} :: {t}", st)
        if cx and cx != "NA":
            put(f"{f} :: {cx} / {t}", st)
    complete = "D4X_COMPLETE" in text
    hit, miss = [], []
    for n in trig:
        st = rows.get(" ".join(n.split()))
        if st == "fail":
            hit.append(n)
        elif st != "ok":
            miss.append(n)
    other = max(sum(1 for v in rows.values() if v == "fail") // 2 - len(hit), 0)
    if not complete or not n_tests:
        return "BLOCKED", hit, miss, other
    if side == "buggy":
        if hit:
            return "FAIL_AS_EXPECTED", hit, miss, other
        return ("UNEXPECTED_PASS" if not miss else "BLOCKED"), hit, miss, other
    if hit:
        return "UNEXPECTED_FAIL", hit, miss, other
    return ("PASS" if not miss else "BLOCKED"), hit, miss, other


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
    lines = text.splitlines()
    failed, locs = [], set()
    for i, ln in enumerate(lines):
        if _re.match(r"\s*\d+\) test ", ln):
            failed.append(ln.strip())
            # ExUnit prints the failing test's `path:line` on the next line; cases
            # may name their trigger as `path:line` (ELIXIR-027), not by title.
            for nxt in lines[i + 1:i + 3]:
                if _re.match(r"\s*\S+\.exs?:\d+\s*$", nxt):
                    locs.add(nxt.strip())
                    break
    hit = [n for n in names if any(n in f for f in failed) or n.strip() in locs]
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
        # `var tests = [XCTestCaseEntry]()` passed to XCTMain without ever being
        # filled: modern SwiftPM accepts it as the entry point and runs 0 tests
        # (SWIFT-D042).
        if lm.parent == root:
            decl = _re.search(r"var\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\[XCTestCaseEntry\]\(\)", text)
            if decl:
                v = _re.escape(decl.group(1))
                if (_re.search(rf"XCTMain\(\s*{v}\s*\)", text)
                        and not _re.search(rf"\b{v}\s*(?:\+=|\.append\s*\()", text)):
                    return True
    return False


def _run_side(args, p, c, side, work, lang, mode, image):
    if lang == "kotlin":
        _sdk = os.path.expanduser("~/d4x/android-sdk")
        if os.path.isdir(_sdk):
            os.environ.setdefault("ANDROID_HOME", _sdk)
            os.environ.setdefault("ANDROID_SDK_ROOT", _sdk)
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
        ccmd = wrap_container(ccmd, img, wt, net=os.environ.get("D4X_CONTAINER_NET") == "1") if ccmd else None
        tcmd = wrap_container(tcmd, img, wt) if tcmd else None
    if args.dry_run:
        print(f"{side}: compile={ccmd}")
        print(f"{side}: test={tcmd}")
        return {"side": side, "compile_rc": None, "test_rc": None,
                "outcome": "DRY_RUN", "applied": applied}
    # Monorepo cases declare build.directory (e.g. pkgs/args, sembast). Running the
    # analyzer/tests from the repo root analyzed the whole monorepo (DART-1123:
    # 17888 issues) and failed both sides at the compile gate. Patches still apply
    # at the repo root; only the commands run in the package directory.
    run_cwd = wt
    if mode != "container":
        _bd = (c.get("build") or {}).get("directory")
        if isinstance(_bd, str) and _bd not in ("", ".") and (wt / _bd).is_dir():
            run_cwd = wt / _bd
    # Julia: each case pins its own Julia (case.json language_version, e.g.
    # "Julia 1.12.7"); a Manifest resolved by another minor version fails with
    # "Could not locate the source code for the X_jll package". Use ~/d4x/julia-<ver>
    # when it exists, else fall back to whatever `julia` is on PATH.
    if lang == "julia" and mode != "container":
        _jv = re.search(r"(\d+\.\d+\.\d+)", str(c.get("language_version") or ""))
        if _jv:
            _jd = Path(os.environ.get("D4X_HOME") or Path.home() / "d4x") / f"julia-{_jv.group(1)}" / "bin"
            if (_jd / "julia").is_file():
                os.environ["PATH"] = f"{_jd}{os.pathsep}{os.environ.get('PATH', '')}"
    compile_rc = 0
    if ccmd:
        compile_rc, _ = run_command(ccmd, run_cwd, timeout, logdir / f"{side}-compile.log")
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
    test_rc, _ = run_command(tcmd, run_cwd, timeout, logdir / f"{side}-test.log")
    # Opt-in D4X_ELIXIR_RERUN_FAILED=<n>: after a failing fixed-side `mix test`, rerun only the
    # failed tests with `mix test --failed` (up to n times). Phoenix's WebSocketChannelsTest
    # restarts one endpoint on fixed port 5807 in every test; the previous listener is not always
    # released yet, so a random test dies with :eaddrinuse (ELIXIR-051: a different test in each of
    # 9 runs, also with --max-cases 1 and --seed 0). A test that fails again in every rerun stays
    # a failure. The first run's log is kept as is; reruns go to <side>-test-rerun<i>.log.
    _rerun_final, _rerun_info = None, {}
    _rr = os.environ.get("D4X_ELIXIR_RERUN_FAILED")
    if (lang == "elixir" and side == "fixed" and _rr and test_rc != 0
            and isinstance(tcmd, list) and tcmd and "mix test" in str(tcmd[-1])):
        _cur = set(elixir_failed_names(logdir / f"{side}-test.log"))
        for _i in range(1, int(_rr) + 1):
            if not _cur:
                break
            _rcmd = list(tcmd)
            _rcmd[-1] = _rcmd[-1].replace("mix test", "mix test --failed", 1)
            _rlog = logdir / f"{side}-test-rerun{_i}.log"
            run_command(_rcmd, run_cwd, timeout, _rlog)
            _rtxt = _rlog.read_text(encoding="utf-8", errors="replace") if _rlog.is_file() else ""
            if not re.search(r"\d+ tests?, \d+ failures?", _rtxt):
                _rerun_info["rerun%d" % _i] = "no ExUnit summary; rerun ignored"
                _cur = None
                break
            _cur = set(elixir_failed_names(_rlog))
            _rerun_info["rerun%d" % _i] = sorted(_cur)
        _rerun_final = _cur
    extra = {}
    names = [n for n in (c.get("triggering_tests") or c.get("trigger_tests") or [])
             if isinstance(n, str)]
    dtrig = [e for e in (c.get("triggering_tests") or c.get("trigger_tests") or [])
             if isinstance(e, dict)]
    rtrig = []
    if lang == "r" and os.environ.get("D4X_R_TRIGGERS"):
        _rf = Path(os.environ["D4X_R_TRIGGERS"]) / f"{p.parent.name}.txt"
        if _rf.is_file():
            rtrig = [l.strip() for l in _rf.read_text(encoding="utf-8").splitlines() if l.strip()]
    if lang == "elixir" and names:
        outcome, hit, other = elixir_verdict(side, logdir / f"{side}-test.log", names)
        extra = {"trigger_failed": hit, "other_failures": other}
        if side == "fixed" and outcome == "PASS":
            # canonical_test_policy: every remaining failure must be listed in
            # validation/excluded-tests.json and reproduced in upstream GOLD.
            checked, unlisted = elixir_unlisted_failures(
                logdir / f"{side}-test.log", p.parent / "validation" / "excluded-tests.json")
            extra["exclusions_checked"] = checked
            if checked and unlisted and _rerun_final is not None:
                extra["flaky_recovered"] = [n for n in unlisted if n not in _rerun_final][:20]
                extra["reruns"] = _rerun_info
                unlisted = [n for n in unlisted if n in _rerun_final]
            if checked and unlisted:
                outcome = "UNEXPECTED_FAIL"
                extra["unlisted_failures"] = unlisted[:20]
    elif lang == "r" and rtrig:
        outcome, hit, miss, other = r_verdict(side, logdir / f"{side}-test.log", rtrig)
        extra = {"verdict_basis": "trigger_tests", "trigger_failed": hit,
                 "trigger_missing": miss, "other_failures": other}
    elif lang == "dart" and dtrig:
        outcome, hit, other = dart_verdict(side, logdir / f"{side}-test.log", dtrig)
        extra = {"verdict_basis": "trigger_tests", "trigger_failed": hit,
                 "other_failures": other}
    elif (lang == "kotlin" and side == "fixed" and test_rc != 0
          and (p.parent / "validation" / "excluded-tests.json").is_file()):
        _tc = [str(n).split("#")[0].split(".")[-1] for n in names if "." in str(n) or str(n)]
        _ok, _names, _unl = kotlin_excluded_verdict(
            logdir / f"{side}-test.log", p.parent / "validation" / "excluded-tests.json", _tc)
        outcome = "PASS" if _ok else "UNEXPECTED_FAIL"
        extra = {"verdict_basis": "excluded_tests", "excluded_failures": _names,
                 "unlisted_failures": _unl[:20]}
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
