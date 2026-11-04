#!/usr/bin/env python3
"""Run the declared ArkTS trigger differential on the local OpenHarmony emulator."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path


ROOT = Path("/home/yifeipei/tools/Defects")
RUN_ROOT = Path(os.environ.get("D4X_ARKTS_RUN_ROOT", "/home/yifeipei/d4x/replay-arkts-v2"))
REPO = Path("/home/yifeipei/d4x/replay-20261031/ARKTS-001/repo.git")
HDCS = Path("/home/yifeipei/d4x/arkts-toolchain/sdk/3.2/ohos-sdk/toolchains/hdc")
HYPIUM_TGZ = Path("/home/yifeipei/d4x/hypium-pack/ohos-hypium-1.0.6.tgz")
NODE_HOME = Path("/home/yifeipei/d4x/node-v16.20.2")
JAVA_HOME = Path("/home/yifeipei/d4x/jdk-21")
SDK_MANAGER_HOME = Path("/home/yifeipei/d4x/arkts-sdk-manager")
# Full SDKs: official ohos-sdk package + interface_sdk-js api/ declarations
# (see arkts_build_full_sdk.sh). The official package omits many .d.ts files.
SDK_FULL_ROOT = Path("/home/yifeipei/d4x/arkts-sdk-full")
SDK_BY_API = {a: SDK_FULL_ROOT / a for a in ("9", "10", "11", "12")}
# ARKTS-046/049 are old API 9 projects (package.json + hvigor 1.2.2) written against the
# 3.2-Beta3 declarations (@ohos.application.Ability); they get the 9b3 variant.
LEGACY_API9_CASES = {"ARKTS-046", "ARKTS-049"}
TARGET = os.environ.get("D4X_ARKTS_TARGET", "127.0.0.1:55556")


def load_d4x():
    spec = importlib.util.spec_from_file_location("d4x_module", ROOT / "scripts" / "d4x.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


D4X = load_d4x()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd, cwd=None, log=None, timeout=1800, env=None):
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        out = log.open("w", encoding="utf-8", errors="replace")
    else:
        out = subprocess.PIPE
    printable = " ".join(str(x) for x in cmd)
    if log:
        out.write("$ " + printable + "\n\n")
        out.flush()
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env,
                           stdout=out, stderr=subprocess.STDOUT if log else subprocess.PIPE,
                           text=True, timeout=timeout)
        if log:
            out.write(f"\nRC={p.returncode}\n")
            out.close()
        return p.returncode
    except subprocess.TimeoutExpired:
        if log:
            out.write(f"\nTIMEOUT after {timeout}s\n")
            out.close()
        return 124
    except OSError as e:
        if log:
            out.write(f"\nOSERROR {e}\n")
            out.close()
        return 127


def clean_path(path: Path):
    if path.exists() or path.is_symlink():
        shutil.rmtree(path)


def shadow_case(case_path: Path, c: dict, base: Path) -> Path:
    """Return a case.json path whose test.patch uses repository-root paths.

    Seven cases (021,022,026,032,037,043,047) ship test.patch with paths relative
    to project_root ("entry/src/ohosTest/..."), while the checkout root is the
    repository root. The patch content is unchanged; only the a/ b/ path prefix is.
    """
    root = str(c.get("project_root") or "").strip("/")
    tp = case_path.parent / "patches" / "test.patch"
    if not root or not tp.is_file():
        return case_path
    txt = tp.read_text(encoding="utf-8", errors="surrogateescape")
    first = re.search(r"^diff --git a/(\S+)", txt, re.M)
    if not first or first.group(1).startswith(root + "/"):
        return case_path
    dst = base / "_shadow" / case_path.parent.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(case_path.parent, dst)
    def fix(m):
        return m.group(1) + root + "/" + m.group(2)
    new = re.sub(r"^(diff --git a/)(\S+)", fix, txt, flags=re.M)
    new = re.sub(r"^(diff --git a/\S+ b/)(\S+)", fix, new, flags=re.M)
    new = re.sub(r"^(--- a/)(\S+)", fix, new, flags=re.M)
    new = re.sub(r"^(\+\+\+ b/)(\S+)", fix, new, flags=re.M)
    (dst / "patches" / "test.patch").write_text(new, encoding="utf-8", errors="surrogateescape")
    return dst / "case.json"


def resolve_project_root(wt: Path, root: str):
    """046/049 record project_root without the leading code/SuperFeature/."""
    p = wt / root
    if p.is_dir():
        return p
    hits = [h for h in wt.glob("code/**/" + root) if h.is_dir()]
    return hits[0] if len(hits) == 1 else p


def make_worktree(case_path: Path, c: dict, cid: str, side: str, base: Path):
    wt = base / cid / side
    wt.parent.mkdir(parents=True, exist_ok=True)
    clean_path(wt)
    rev = c["buggy_revision"] if side == "buggy" else c["fixed_revision"]
    rc = run(["git", "--git-dir", str(REPO), "worktree", "add", "--force", "--detach", str(wt), rev],
             log=base / cid / "logs" / f"{side}-checkout.log", timeout=900)
    if rc != 0:
        return None, [f"checkout_rc={rc}"]
    try:
        applied = D4X.apply_patches(shadow_case(case_path, c, base), side, wt, True)
        return wt, [str(x) for x in applied]
    # d4x.apply_patches uses SystemExit for a non applicable declared patch.
    # Treat that as a per-case BLOCKED result so one stale case cannot abort the
    # remaining ArkTS batch.
    except BaseException as e:
        return wt, [f"patch_error={type(e).__name__}: {e}"]


def sdk_for(case_dir: Path):
    lock = json.loads((case_dir / "environment.lock.json").read_text(encoding="utf-8"))
    api = str(lock.get("compile_sdk"))
    if case_dir.name in LEGACY_API9_CASES:
        return SDK_FULL_ROOT / "9b3", api, lock
    return SDK_BY_API.get(api), api, lock


def flatten(x):
    if isinstance(x, list):
        out = []
        for y in x:
            out.extend(flatten(y))
        return out
    return [x]


def legacy_sdk_root(sdk: Path) -> Path:
    """hvigor 1.x wants <root>/<component>/<version>/ ; build such a root of symlinks."""
    root = Path("/tmp/d4x-legacy-sdk-" + sdk.name)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for comp in ("ets", "js", "native", "previewer", "toolchains"):
        ver = json.loads((sdk / comp / "oh-uni-package.json").read_text())["version"]
        (root / comp).mkdir()
        (root / comp / ver).symlink_to(sdk / comp)
    return root


def cached_hvigor_js(version: str):
    """Path of bin/hvigor.js for a hvigor version already installed by an earlier hvigorw run."""
    base = Path.home() / ".hvigor" / "project_caches"
    hits = sorted(base.glob(f"*/workspace/node_modules/.pnpm/@ohos+hvigor@{version}/node_modules/@ohos/hvigor/bin/hvigor.js"))
    return hits[0] if hits else None


def hvigor_version_of(project: Path, lock: dict):
    return str(lock.get("declared_hvigor_version") or "")


def is_legacy_project(project: Path) -> bool:
    return not (project / "hvigor").is_dir() and (project / "package.json").is_file()


def command_for(c: dict, side: str, project: Path):
    if is_legacy_project(project):
        row = ((c.get("build_commands") or {}).get(side) or {}).get("app") or []
        args = flatten(row[2:]) if len(row) >= 3 else ["--mode", "module", "-p", "module=entry@default",
                                                       "-p", "product=default", "--no-daemon", "assembleHap"]
        return [str(project / "node_modules" / ".bin" / "hvigor")] + [str(x) for x in args]
    return command_for_new(c, side, project)


def command_for_new(c: dict, side: str, project: Path):
    # The repository records an absolute reference path as the first two command
    # elements. Replace both with the checkout's hvigorw while retaining flags.
    row = ((c.get("build_commands") or {}).get(side) or {}).get("app") or []
    if len(row) >= 3:
        args = flatten(row[2:])
    else:
        args = ["--mode", "module", "-p", "module=entry@default", "-p", "product=default",
                "--no-daemon", "assembleHap"]
    return ["bash", str(project / "hvigorw")] + [str(x) for x in args]


def test_command(c: dict):
    """Build the `aa test` command line.

    Several trigger tests must be passed to `-s class` as ONE comma separated value.
    The case files store them either as a nested list (test_command_template) or as
    separate words; joined with spaces, aa test silently runs only the first one
    ("Tests run: 1"), which hides failures of the others (ARKTS-009, 011).
    """
    tpl = c.get("test_command_template") or []
    if tpl:
        row = list(tpl)
        out = []
        for x in row:
            if isinstance(x, list):
                out.append(",".join(str(y) for y in flatten(x)))
            else:
                out.append(str(x))
        row = out
    else:
        bundle = str(c.get("bundle") or "")
        runner = str(c.get("runner") or "/ets/TestRunner/OpenHarmonyTestRunner")
        targets = [str(t) for t in flatten(c.get("target") or [])]
        if not bundle or not targets:
            return []
        row = ["hdc", "-t", "127.0.0.1:5555", "shell", "aa", "test", "-b",
               bundle, "-m", "entry_test", "-s", "unittest", runner,
               "-s", "class", ",".join(targets)]
    # old templates may still carry the trailing tests as separate words
    # hypium validates `-s class` values with /^[A-Za-z][\\w#,.]*$/, so a test name with spaces
    # (ARKTS-006, 014) is rejected as "invalid". `-s suite` + `-s itName` match by equality
    # and accept any characters, so split "Suite#name with spaces" into those two.
    if "class" in row:
        ci = len(row) - 1 - row[::-1].index("class")
        if ci + 1 < len(row) and any(" " in part for part in row[ci + 1].split(",")):
            parts = row[ci + 1].split(",")
            suites = sorted({p.split("#")[0] for p in parts})
            names = [p.split("#", 1)[1] for p in parts if "#" in p]
            row = row[:ci - 1] + ["-s", "suite", ",".join(suites), "-s", "itName", ",".join(names)] + row[ci + 2:]
    if "timeout" not in row and "-s" in row:
        tmo = ["-s", "timeout", os.environ.get("D4X_ARKTS_TEST_TIMEOUT_MS", "60000")]
        key = "class" if "class" in row else ("suite" if "suite" in row else None)
        if key:
            ki = len(row) - 1 - row[::-1].index(key)
            row = row[:ki - 1] + tmo + row[ki - 1:]
    if "class" in row:
        i = len(row) - 1 - row[::-1].index("class")
        tail = row[i + 1:]
        if len(tail) > 1:
            row = row[:i + 1] + [",".join(tail)]
    row = [str(HDCS) if x == "hdc" else str(x).replace("127.0.0.1:5555", TARGET) for x in row]
    # hdc joins the words after `shell` with spaces and the device shell splits them again,
    # so a test name that contains spaces (ARKTS-006, 014) must be quoted as part of one string.
    if "shell" in row:
        i = row.index("shell")
        import shlex
        row = row[:i + 1] + [" ".join(shlex.quote(w) for w in row[i + 1:])]
    return row


def scale_test_delays(project: Path, factor: float):
    """Multiply the waits of the UI tests (ohosTest sources) by `factor`.

    The tests were written for a device where an app window exists about 1 s after startAbility. On the emulator
    it exists after about 2 s and UiTest then walks a window list that is still changing, so controls that do
    exist are reported as "Component not exist". Scaling the *test* waits (never the application) leaves the
    assertions untouched. Handles `delayMs(<int>)` and `const X_DELAY/WAIT/SLEEP/TIMEOUT...: number = <int>` (TIME_OUT is the wait of
    `waitAbilityMonitor` in ARKTS-050).
    Returns the list of changed files; empty when factor == 1.
    """
    if factor == 1:
        return []
    import re as _re
    changed = []
    for f in project.glob("**/src/ohosTest/**/*.ets"):
        if "oh_modules" in f.parts or "node_modules" in f.parts:
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        n = _re.sub(r"delayMs\((\d+)\)", lambda m: "delayMs(%d)" % round(int(m.group(1)) * factor), t)
        n = _re.sub(r"(const\s+[A-Z_]*(?:DELAY|WAIT|SLEEP|TIME_?OUT)[A-Z_]*\s*(?::\s*number)?\s*=\s*)(\d+)",
                    lambda m: m.group(1) + str(round(int(m.group(2)) * factor)), n)
        if n != t:
            f.write_text(n, encoding="utf-8")
            changed.append(str(f.relative_to(project)))
    return changed


def apply_local_deps(case_dir: Path, side: str, project: Path):
    """Apply the case's declared local dependency injection (environment.lock.json).

    The lock records, per side, the in-repo library modules that the build needs under
    oh_modules ("local_file") and the resources of those modules that must be merged
    into the app ("dependency_resource_compat"). Without this, hvigor reports
    "Cannot find module '@ohos/xxx'" (12 cases: 008 020 025 026 028 030 031 032 035 040 041 048).
    Returns a list of human readable actions.
    """
    acts = []
    try:
        lock = json.loads((case_dir / "environment.lock.json").read_text(encoding="utf-8"))
        sd = lock["environment_contract"]["sides"][side]
    except Exception as e:
        return [f"lock_unreadable:{e}"]
    for it in (sd.get("local_file") or {}).get("injected") or []:
        src = project / it["source_relative_to_project"]
        dst = project / it["target_relative_to_project"]
        if not src.is_dir():
            acts.append(f"MISSING_SRC:{src}")
            continue
        if dst.exists():
            shutil.rmtree(dst) if not dst.is_symlink() else dst.unlink()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("oh_modules", "build", ".hvigor"))
        acts.append(f"local_file:{it['package']}")
    for cp in (sd.get("dependency_resource_compat") or {}).get("copies") or []:
        base = project / cp["target_relative_to_project"]
        # resources live in <package>/src/main/resources/<source_resource>
        src = base / "src" / "main" / "resources" / cp["source_resource"]
        if not src.is_file():
            src = project / cp["source_relative_to_project"] / "src" / "main" / "resources" / cp["source_resource"]
        dst = project / cp["target_resource"]
        if not src.is_file():
            acts.append(f"MISSING_RES:{cp['source_resource']}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.suffix == ".json" and "element" in str(dst):
            try:
                a = json.loads(dst.read_text(encoding="utf-8"))
                b = json.loads(src.read_text(encoding="utf-8"))
                key = next((k for k in b if isinstance(b[k], list)), None)
                if key:
                    have = {x.get("name") for x in a.get(key, [])}
                    a.setdefault(key, []).extend(x for x in b[key] if x.get("name") not in have)
                    dst.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
                    acts.append(f"res_merge:{cp['source_resource']}")
                    continue
            except Exception:
                pass
            continue  # existing app resource wins
        if not dst.exists():
            shutil.copy2(src, dst)
            acts.append(f"res_copy:{cp['source_resource']}")
    return acts


def hap(project: Path, output: str):
    paths = list(project.glob(f"**/build/**/outputs/{output}/*.hap"))
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def inject_hypium(project: Path):
    """Materialize the exact case-declared @ohos/hypium 1.0.6 package.

    The repository's environment locks explicitly record Hypium injection.  The
    public project checkout does not carry the package, so hvigor otherwise
    reports the test module as an unresolved external dependency.
    """
    if not HYPIUM_TGZ.is_file():
        return False
    dest = project / "oh_modules" / "@ohos" / "hypium"
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = project / ".d4x-hypium-extract"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    with tarfile.open(HYPIUM_TGZ, "r:gz") as tf:
        tf.extractall(tmp)
    src = tmp / "package"
    shutil.copytree(src, dest)
    (dest / ".d4x-injected").write_text("@ohos/hypium 1.0.6\n", encoding="utf-8")
    shutil.rmtree(tmp)
    return True


def parse_report(log: Path, targets):
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    m = None
    for line in text.splitlines():
        if "OHOS_REPORT_RESULT:" in line:
            m = re.search(r"Tests run:\s*(\d+),\s*Failure:\s*(\d+),\s*Error:\s*(\d+),\s*Pass:\s*(\d+)(?:,\s*Ignore:\s*(\d+))?", line)
    seen = []
    for line in text.splitlines():
        z = re.search(r"OHOS_REPORT_STATUS: test=(.*)$", line)
        if z:
            seen.append(z.group(1).strip())
    errors = bool(re.search(r"(?:Error in |OHOS_REPORT_STATUS_CODE:\s*-1|Failure:\s*[1-9]|Error:\s*[1-9])", text))
    summary = None
    if m:
        summary = {"tests": int(m.group(1)), "failures": int(m.group(2)),
                   "errors": int(m.group(3)), "passes": int(m.group(4)),
                   "ignored": int(m.group(5) or 0)}
        errors = errors or summary["failures"] > 0 or summary["errors"] > 0
    target_seen = {t: any(t in s or s in t for s in seen) for t in targets}
    return {"summary": summary, "status_tests": seen, "target_seen": target_seen,
            "reported_error": errors, "raw_sha256": sha256(log) if log.is_file() else None}


def install_and_test(c: dict, side: str, project: Path, sdk: Path, logdir: Path, targets):
    bundle = str(c.get("bundle") or "")
    app = hap(project, "default")
    test = hap(project, "ohosTest")
    if not app or not test:
        return {"compile_rc": 0, "test_rc": None, "outcome": "BLOCKED",
                "reason": "HAP_NOT_FOUND", "app_hap": str(app) if app else None,
                "test_hap": str(test) if test else None}
    uninstall = run([str(HDCS), "-t", TARGET, "uninstall", bundle], log=logdir / f"{side}-uninstall.log", timeout=120)
    app_rc = run([str(HDCS), "-t", TARGET, "install", "-r", str(app)], log=logdir / f"{side}-app-install.log", timeout=300)
    test_rc = run([str(HDCS), "-t", TARGET, "install", "-r", str(test)], log=logdir / f"{side}-test-install.log", timeout=300)
    if app_rc != 0 or test_rc != 0:
        return {"compile_rc": 0, "test_rc": None, "outcome": "BLOCKED",
                "reason": "HDC_INSTALL", "install_rc": {"uninstall": uninstall, "app": app_rc, "test": test_rc},
                "app_hap": str(app), "test_hap": str(test)}
    tcmd = test_command(c)
    if not tcmd:
        return {"compile_rc": 0, "test_rc": None, "outcome": "BLOCKED",
                "reason": "TEST_COMMAND_MISSING", "app_hap": str(app),
                "test_hap": str(test)}
    tlog = logdir / f"{side}-test.log"
    # Warm-up (empirical). On ARKTS-012 the test failed with "Component not exist" twice when the
    # app was already in the foreground, and passed once the app had been force-stopped right
    # before `aa test`. The cause was not isolated; this start / wait / force-stop sequence
    # reproduces the passing condition. Disable with D4X_ARKTS_WARMUP_S=0.
    warm = int(os.environ.get("D4X_ARKTS_WARMUP_S", "40"))
    if warm > 0:
        main_ability = str(c.get("main_ability") or "")
        start = [str(HDCS), "-t", TARGET, "shell", f"aa start -b {bundle}" + (f" -a {main_ability}" if main_ability else "")]
        if not main_ability:
            # resolve the entry ability from the installed package
            out = subprocess.run([str(HDCS), "-t", TARGET, "shell", f"bm dump -n {bundle}"],
                                 capture_output=True, text=True).stdout
            m = re.search(r'"mainAbility":\s*"([^"]+)"', out) or re.search(r'"mainElementName":\s*"([^"]+)"', out)
            if m:
                start = [str(HDCS), "-t", TARGET, "shell", f"aa start -b {bundle} -a {m.group(1)}"]
        run(start, log=logdir / f"{side}-warmup.log", timeout=120)
        time.sleep(warm)
        if os.environ.get("D4X_ARKTS_WARMUP_STOP", "0") == "1":
            run([str(HDCS), "-t", TARGET, "shell", f"aa force-stop {bundle}"], log=logdir / f"{side}-warmup-stop.log", timeout=60)
            time.sleep(3)
        else:
            # leave the app running in the foreground: the tests wait 1 to 2.4 s after startAbility, but a cold
            # start on the emulator needs about 3.5 s before the window exists.
            time.sleep(2)
    # Attempts policy (D4X_ARKTS_ATTEMPTS, default 1). UI tests on the emulator are timing dependent: the same
    # build can pass or fail with "Component not exist". With N > 1 the fixed side counts as PASS when any
    # attempt passes, and the buggy side counts as failing only when EVERY attempt fails. All attempts are
    # recorded in result.json ("attempts"); a result that needed more than one attempt is flagged flaky.
    n_att = max(1, int(os.environ.get("D4X_ARKTS_ATTEMPTS", "1")))
    attempts = []
    chosen = None
    for k in range(n_att):
        alog = logdir / (f"{side}-test.log" if k == 0 else f"{side}-test-attempt{k + 1}.log")
        if k > 0:
            run([str(HDCS), "-t", TARGET, "shell", f"aa force-stop {bundle}"], log=logdir / f"{side}-stop{k + 1}.log", timeout=60)
            time.sleep(3)
        arc = run(tcmd, log=alog, timeout=900)
        ap = parse_report(alog, targets)
        asum = ap.get("summary")
        passed = bool(asum and not ap["reported_error"] and all(ap["target_seen"].values()) and asum["tests"] > 0 and arc == 0)
        attempts.append({"log": alog.name, "rc": arc, "passed": passed,
                         "summary": asum, "reported_error": ap["reported_error"]})
        chosen = (alog, arc, ap)
        if side == "fixed" and passed:
            break
        if side == "buggy" and passed:      # a buggy-side pass ends the search: the trigger did not fail
            break
    tlog, trc, parsed = chosen
    if tlog.name != f"{side}-test.log":
        shutil.copyfile(tlog, logdir / f"{side}-test.log")
        tlog = logdir / f"{side}-test.log"
    summary = parsed.get("summary")
    log_text = tlog.read_text(encoding="utf-8", errors="replace") if tlog.is_file() else ""
    crashed = ("App died" in log_text and "test=" in log_text)
    if not summary and crashed and side == "buggy":
        # The test ability started the target test (OHOS_REPORT_STATUS test=...) and the app process
        # died before a result was written: the crash is the failure the fix removes (ARKTS-016).
        outcome = "FAIL_AS_EXPECTED"
        reason = "declared_trigger_app_crash"
    elif not summary:
        outcome = "BLOCKED"
        reason = "NO_OHOS_REPORT_RESULT"
    elif side == "buggy":
        outcome = "FAIL_AS_EXPECTED" if parsed["reported_error"] and all(parsed["target_seen"].values()) else "UNEXPECTED_PASS"
        reason = "declared_trigger_error" if outcome == "FAIL_AS_EXPECTED" else "trigger_not_failed_or_not_seen"
    else:
        outcome = "PASS" if (not parsed["reported_error"] and all(parsed["target_seen"].values()) and summary["tests"] > 0 and trc == 0) else "UNEXPECTED_FAIL"
        reason = "declared_trigger_pass" if outcome == "PASS" else "fixed_trigger_failed_or_missing"
    flaky = n_att > 1 and len(attempts) > 1 and (attempts[-1]["passed"] if side == "fixed" else False)
    return {"compile_rc": 0, "test_rc": trc, "outcome": outcome, "reason": reason,
            "attempts": attempts, "flaky": flaky, "attempts_allowed": n_att,
            "install_rc": {"uninstall": uninstall, "app": app_rc, "test": test_rc},
            "app_hap": str(app), "test_hap": str(test), "parsed": parsed}


def run_case(cid: str):
    case_path = ROOT / "cases" / "arkts" / cid / "case.json"
    case_dir = case_path.parent
    c = json.loads(case_path.read_text(encoding="utf-8"))
    base = RUN_ROOT
    out = base / cid
    logdir = out / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    sdk, api, lock = sdk_for(case_dir)
    result = {"schema_version": 1, "case_id": cid, "language": "arkts", "mode": "device_emulator",
              "oracle": {}, "environment": {"sdk_api": api, "sdk_path": str(sdk) if sdk else None,
              "hdc_target": TARGET, "emulator": "oniro_emulator_v6.1", "compile_scope": "app_and_ohosTest",
              "test_scope": "declared_trigger_command_only"}, "patches": {}, "sides": {},
              "generated_at": now()}
    try:
        oracle_file = ROOT / "metadata" / "oracle.jsonl"
        for line in oracle_file.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("case_id") == cid:
                result["oracle"] = json.loads(line)
                break
    except Exception:
        pass
    targets = c.get("target")
    targets = [str(x) for x in (targets if isinstance(targets, list) else [targets]) if x]
    result["targets"] = targets
    if not sdk or not sdk.is_dir():
        result["verdict"] = "BLOCKED"
        result["blocking_reason"] = "SDK_API_NOT_INSTALLED"
        result["generated_at"] = now()
        (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return result
    env = os.environ.copy()
    # Hvigor 3.x uses the SDK-manager layout (root/<api>/{ets,js,...}), while
    # the API 9 projects still use the legacy flat root. The manager overlay
    # contains symlinks to the downloaded component trees and keeps the
    # declared API version visible to Hvigor's compatibility check.
    env_sdk = sdk if api == "9" else SDK_FULL_ROOT
    component_sdk = sdk
    env.update({"NODE_HOME": str(NODE_HOME), "JAVA_HOME": str(JAVA_HOME),
                "DEVECO_SDK_HOME": str(sdk if api == "9" else SDK_FULL_ROOT), "OHOS_SDK_HOME": str(sdk),
                "OHOS_BASE_SDK_HOME": str(env_sdk), "HOS_SDK_HOME": str(env_sdk),
                "PATH": f"{JAVA_HOME}/bin:{NODE_HOME}/bin:{component_sdk}/toolchains:{env.get('PATH','')}",
                "npm_config_registry": "https://registry.npmjs.org/"})
    sides_ok = True
    for side in ("buggy", "fixed"):
        wt, applied = make_worktree(case_path, c, cid, side, base)
        result["patches"][side] = applied
        if wt is None or any(x.startswith("patch_error") for x in applied):
            result["sides"][side] = {"compile_rc": None, "test_rc": None, "outcome": "BLOCKED", "reason": "CHECKOUT_OR_PATCH"}
            sides_ok = False
            continue
        project = resolve_project_root(wt, str(c.get("project_root") or "."))
        if project.is_dir() and not (project / "hvigorw").is_file() and (project / "hvigor").is_dir():
            # hvigor 4.x projects that ship hvigor/hvigor-config.json5 without the hvigorw wrapper (ARKTS-033)
            hv = cached_hvigor_js(hvigor_version_of(project, lock))
            if hv is not None:
                (project / "hvigorw").write_text(
                    "#!/bin/bash\nexec node %s \"$@\"\n" % shlex.quote(str(hv)), encoding="utf-8")
        legacy = project.is_dir() and is_legacy_project(project)   # package.json + hvigor 1.x, no hvigorw
        if not project.is_dir() or (not legacy and not (project / "hvigorw").is_file()):
            result["sides"][side] = {"compile_rc": None, "test_rc": None, "outcome": "BLOCKED", "reason": "PROJECT_OR_HVIGOR_MISSING", "project": str(project)}
            sides_ok = False
            continue
        (project / ".npmrc").write_text("registry=https://registry.npmjs.org/\n@ohos:registry=https://repo.harmonyos.com/npm/\n", encoding="utf-8")
        if (project / "hvigorw").is_file():
            os.chmod(project / "hvigorw", 0o755)
        hypium_ok = inject_hypium(project)
        _scale = float(os.environ.get("D4X_ARKTS_DELAY_SCALE", "1"))
        scaled = scale_test_delays(project, _scale)
        result.setdefault('delay_scale', {})[side] = {"factor": _scale, "files": scaled}
        dep_acts = apply_local_deps(case_path.parent, side, project)
        result.setdefault('local_deps', {})[side] = dep_acts
        build_env = env
        if is_legacy_project(project):
            run(["npm", "install", "--no-audit", "--no-fund", "--loglevel=error"], cwd=project,
                log=logdir / f"{side}-npm-install.log", timeout=900, env=env)
            lroot = legacy_sdk_root(sdk)
            build_env = dict(env)
            build_env.update({"DEVECO_SDK_HOME": str(lroot), "OHOS_SDK_HOME": str(lroot),
                              "OHOS_BASE_SDK_HOME": str(lroot), "HOS_SDK_HOME": str(lroot)})
        appcmd = command_for(c, side, project)
        testcmd = list(appcmd)
        if "module=entry@default" in testcmd:
            testcmd[testcmd.index("module=entry@default")] = "module=entry@ohosTest"
        app_rc = run(appcmd, cwd=project, log=logdir / f"{side}-app-build.log", timeout=1800, env=build_env)
        if app_rc == 0:
            test_rc = run(testcmd, cwd=project, log=logdir / f"{side}-test-build.log", timeout=1800, env=build_env)
        else:
            test_rc = None
        if app_rc != 0 or test_rc != 0:
            result["sides"][side] = {"compile_rc": app_rc if app_rc != 0 else test_rc, "test_rc": None,
                                      "outcome": "BLOCKED", "reason": "HVIGOR_BUILD", "project": str(project),
                                      "hypium_injected": hypium_ok}
            sides_ok = False
            continue
        result["sides"][side] = install_and_test(c, side, project, sdk, logdir, targets)
        result["sides"][side]["hypium_injected"] = hypium_ok
        if result["sides"][side]["outcome"] in ("BLOCKED", "UNEXPECTED_FAIL", "UNEXPECTED_PASS"):
            sides_ok = False
    bo = result["sides"].get("buggy", {}).get("outcome")
    fo = result["sides"].get("fixed", {}).get("outcome")
    if bo == "FAIL_AS_EXPECTED" and fo == "PASS":
        result["verdict"] = "PASS"
    elif bo == "BLOCKED" or fo == "BLOCKED":
        result["verdict"] = "BLOCKED"
    else:
        result["verdict"] = "FAIL"
    result["generated_at"] = now()
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def free_gb(path: Path) -> float:
    st = os.statvfs(str(path))
    return st.f_bavail * st.f_frsize / 1e9


def slim_case(cid: str):
    """Keep logs and result.json, drop both worktrees (they are ~1 GB each)."""
    for side in ("buggy", "fixed"):
        wt = RUN_ROOT / cid / side
        if wt.exists():
            subprocess.run(["git", "--git-dir", str(REPO), "worktree", "remove", "--force", str(wt)],
                           capture_output=True)
            shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(["git", "--git-dir", str(REPO), "worktree", "prune"], capture_output=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    ids = args.case or []
    if args.all:
        ids = sorted(p.parent.name for p in (ROOT / "cases" / "arkts").glob("*/case.json"))
    if not ids:
        raise SystemExit("use --case ID or --all")
    tsv = RUN_ROOT / "cases.tsv"
    if not tsv.exists():
        tsv.write_text("case_id\tverdict\tbuggy_outcome\tfixed_outcome\tgenerated_at\n", encoding="utf-8")
    keep = os.environ.get("D4X_ARKTS_KEEP_WORKTREES") == "1"
    for cid in ids:
        # A full disk turns every later case into a bogus BLOCKED; stop instead.
        if free_gb(RUN_ROOT) < 8:
            raise SystemExit(f"less than 8 GB free under {RUN_ROOT}; stopped before {cid}")
        print(f"[{now()}] START {cid}", flush=True)
        r = run_case(cid)
        if not keep:
            slim_case(cid)
        line = "\t".join([cid, r.get("verdict", ""), r.get("sides", {}).get("buggy", {}).get("outcome", ""),
                           r.get("sides", {}).get("fixed", {}).get("outcome", ""), r.get("generated_at", "")])
        with tsv.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"[{now()}] DONE {cid} {r.get('verdict')}", flush=True)


if __name__ == "__main__":
    main()
