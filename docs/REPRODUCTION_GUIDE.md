# Reproduction guide

This guide defines the common replay protocol for all Defects4X cases. Language-specific toolchain versions are in `env/`.

## 1. Read the case

```bash
python - <<'PY'
import json
case = json.load(open('cases/dart/DART-101/case.json'))
print(json.dumps(case, indent=2)[:4000])
PY
```

Important fields vary slightly by language:

- repository: `repository_url`, `repo_url`, `repository`, or `repository.url`
- revisions: `buggy_revision` / `fixed_revision`, or `commits.buggy` / `commits.fixed`
- patches: `patches`, `patch`, `source_fix`, `trigger`, `trigger_tests`
- environment: `environment.lock.json`, `environment/`, or `environment_file`
- validation: `validation`, `status`, `ledger`

Use the **case's own roles**, not a blanket "apply the fix commit".

## 2. Fetch and patch the upstream source

```bash
python scripts/d4x.py checkout DART-101 --work /tmp/d4x
```

This:

- reads the repository URL and revisions from `case.json`
- clones with `--filter=blob:none`
- creates `buggy` and `fixed` worktrees
- applies the declared trigger/production patches
- never modifies the upstream remote

For offline/air-gapped runs, mirror the repository bundles and set `D4X_SOURCE_CACHE`.

To run the whole protocol:

```bash
python scripts/d4x.py run DART-101 --work /tmp/d4x --dry-run
python scripts/d4x.py run DART-101 --work /tmp/d4x
```

`run` writes `result.json` with compile/test exit codes and the PASS/FAIL verdict.

## 3. Install the toolchain

Follow the language guide:

- Dart: `env/dart.md`
- Julia: `env/julia.md`
- Kotlin: `env/kotlin.md`
- Lua: `env/lua.md`
- Perl: `env/perl.md`
- R: `env/r.md`
- Elixir/Swift: `env/container.md`

Replay notes with the options each case needed: `docs/REPLAY_DART_PERL_JULIA_LUA_R.md`,
`docs/REPLAY_KOTLIN_ELIXIR.md`, `docs/REPLAY_SWIFT.md`.
Why a replay on another host can end BLOCKED or FAIL: `docs/REPLAY_SECOND_HOST_AUDIT.md`.
- ArkTS: `env/device-arkts.md`

Before running a case, check versions:

```bash
dart --version
julia --version
java -version
gradle --version
lua -v
perl -v
R --version
```

If the case has `environment.lock.json`, its versions take precedence over the language-level defaults.

## 4. Apply patches

`d4x checkout` already applies the selected trigger/production patches. If you
need to do it manually, the typical order is:

1. Check out the buggy revision.
2. Apply the **trigger/test patch** (the test that exposes the defect).
3. For the fixed side, apply the **production/source patch**.
4. Do not apply the original upstream fix patch unless the case explicitly says to.

Use the patch paths declared in `case.json`:

```text
patches/original-source.patch
patches/minimized-source.patch
patches/trigger-tests.patch
patches/upstream.patch
```

Always apply with `git apply --check` first.

## 5. Run the trigger

The expected differential is:

- buggy: trigger **fails**
- fixed: trigger **passes**

Use the CLI:

```bash
python scripts/d4x.py run DART-101 --work /tmp/d4x --dry-run
python scripts/d4x.py run DART-101 --work /tmp/d4x
```

`run` writes `<work>/<CASE>/result.json` with per-side compile/test rc and
`FAIL_AS_EXPECTED` / `PASS` / `COMPILE_ERROR` / `BLOCKED` outcomes.

Record:

- exact commands
- exit codes
- stdout/stderr
- JUnit/XML or test-runner report
- toolchain versions
- wall-clock timeout

A timeout is not a semantic failure. A missing SDK/image/device is `BLOCKED`, not `PASS`.

## 6. Report

Open an issue with:

- case ID
- OS/architecture
- toolchain versions
- commands
- expected vs observed
- logs (redact local paths)

## Status vocabulary

| Status | Meaning |
|---|---|
| `SOURCE_REPRODUCIBLE` | source + documented toolchain is sufficient |
| `CONTAINER_REQUIRED` | exact runtime image/digest is required |
| `DEVICE_REQUIRED` | authorized device/SDK/signing is required |
| `BLOCKED` | a required asset is missing |
| `PARTIAL` | some but not all required evidence is available |

## Common pitfalls

- Applying the full upstream fix commit instead of the minimized production patch.
- Running the full suite when the case defines a single triggering test.
- Using a newer SDK than the case lock; old Dart/Julia/Swift projects often fail to resolve.
- Network access during a run that is declared offline.
- Treating a flaky full-suite baseline failure as a trigger failure.
