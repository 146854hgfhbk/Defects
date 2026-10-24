# Clean-install replay notes

These notes record a from-scratch replay on a fresh Ubuntu 24.04.4 x86_64 host
(2 vCPU, 7 GB RAM, no Docker at the start). One case per language was run with
`scripts/d4x.py run <CASE>`. This is a smoke check, not full coverage: one case
per language does not show that the other cases in that language reproduce.

## Result

| Language | Case | Verdict | Notes |
|---|---|---|---|
| Lua | EV-LU-004 | PASS | distro Lua 5.4.6 / LuaRocks 3.8.0 (case records 5.4.8 / 3.11.1) |
| Dart | DART-101 | PASS | SDK 2.19.6 |
| Perl | PERL-002 | PASS | distro Perl 5.38 (case records 5.36) |
| Julia | JULIA-002 | PASS | Julia 1.10.12 |
| Kotlin | KOTLIN-001 | PASS | JDK 17; first Gradle build about 8 minutes, about 6 GB RAM |
| R | BENCH-1 | PASS | R 4.4.3; packages were the latest at install time, not the case lock |
| Elixir | ELIXIR-001 | PASS | public `swerebenchv2` image; 14 unrelated baseline failures on both sides |
| Swift | all 100 cases | 100 PASS in the latest run of each case | five rebuilt images; 36 cases are being re-run with every trigger test name (see below) |
| ArkTS | - | not run | needs a device or emulator |

Swift: all 100 cases were run on the five rebuilt images (5.10.1: 41, 6.1: 13,
6.2.3 v2: 16, v3-sqlite: 18, v4-openssl: 12) and the latest run of every case fails
on the buggy side and passes on the fixed side. The runs were made with several
versions of `d4x` while it was being fixed, so the 100 results do not all come from
the final code. Each case was run once for its latest verdict, apart from the
re-runs described below.

* 98 of the 100 are runtime tests; for each, the fixed-side log shows the named
  trigger test actually ran and passed. The other 2 (SWIFT-D058 and SWIFT-D060) have a
  compile error as their trigger.
* Not finished: `d4x` now passes every distinct trigger test name to `swift test`
  (several `--filter` flags) instead of only the first. That touches 36 cases. Only
  SWIFT-D046 has been re-run with it so far, and it passes (its first test passes on the
  buggy side, the second fails). For the other 35, the buggy side already failed with
  the first name, and more names cannot undo that. The fixed side has NOT been checked
  with all names: one of the other trigger tests could still fail there. Until that
  re-run finishes, the 35 results only cover the first trigger test.
* 56 of the cases ship a `dependency_cache`; none of it was used. Dependencies were
  resolved with network once (`swift package resolve` inside the image) and the replay
  ran with `--network none`. For the cases that were re-run after the runner fixes and
  have a recorded `Package.resolved` with at least one pin, that file was put in place
  before resolving, so the pins were kept; cases with no recorded pins (for example
  SWIFT-D059, D007) had nothing to keep. For the rest SwiftPM picked versions: an audit before those re-runs found 15
  passing cases whose resolved versions differed from the recorded ones; two (D022,
  D027) were re-run with the recorded pins and still pass, the other 13 were not
  re-run. A pass therefore does not show that the originally recorded dependency
  versions reproduce.

## Fixes made to the runner while replaying

* Dart: a bare `dart analyze` also analysed nested sub-packages whose
  dependencies were never resolved (`tool/export_docs` in DART-101), so both
  sides failed to compile. It now analyses `lib`, `bin` and `test` only.
* Julia: the case's `trigger/trigger.jl` and per-side `Project.toml` /
  `Manifest.toml` were never copied into the worktree. They are now staged, and
  the eager `Pkg.precompile()` was replaced by
  `Pkg.instantiate(; allow_autoprecomp=false)` because it failed on JULIA-002
  with `failed to find source of parent package` although the trigger ran fine.
* Kotlin: `trigger-tests.patch` sits at the case root, but patch discovery only
  scanned subdirectories, so the buggy side had no failing test
  (`UNEXPECTED_PASS`). All 100 Kotlin cases keep the file at the root; only
  KOTLIN-001 was run.
* R: the test command did not load the package under test. It now uses
  `package = pkg, load_package = "installed"` and lifts testthat's default
  failure cap. All 100 R cases have `revision_mode =
  fixed_minus_minimized_patch`: the buggy tree is the fixed revision with the
  minimized patch applied, and the fixed side is left untouched.
* Elixir: `case.json` has `"repo": "owner/name"` without a host, which
  `git clone` rejects; `repo_url()` now expands it to a GitHub URL. The verdict
  is taken from the named `triggering_tests` instead of the `mix test` exit
  code, which is non-zero whenever any test fails.
* Swift: a stub `Tests/LinuxMain.swift` that says to pass `--enable-test-discovery`
  made `swift test` abort on both sides (SWIFT-D080, D081); the flag is now added
  when such a stub is detected. If a build fails on a stale `LinuxMain.swift`
  (SWIFT-D085) the compile is retried once with the flag.
* Swift: 12 cases have `artifacts.fixed.equals_upstream_tree == false`. Their
  production patch does not apply to the upstream fix commit, so the fixed tree
  is now built from the base revision plus the trigger and production patches
  (SWIFT-D074, D076, D095 and others). `fetch_sources.py` uses the same revision.
* Swift: five cases hard-code `/opt/swift510/usr/bin/swift` in their build
  commands. Rebuilt images have swift at `/usr/bin/swift`, so the path is rewritten
  to `swift` in container mode (SWIFT-D070, D086, D089, D093, D097).
* Swift: use the trigger patch that `case.json` declares (`patches.trigger_tests.path`).
  Eight cases ship several candidates (`...-compatible`, `...-stable`, ...) and picking
  by file name applied the wrong one (SWIFT-D014, D019, D021, D022, D027, D029, D003,
  D007).
* Swift: apply `patches.build_compatibility` on both sides before the trigger patch.
  Six Swift cases declare one (SWIFT-D003, D005, D015, D024, D025, D041); without it
  they fail to build on the pinned toolchain, for example the OpenSSL 3 macro alias
  `EVP_MD_type` in D003. Two Dart cases also declare one.
* Swift: a root `LinuxMain.swift` that passes an empty, never-filled
  `[XCTestCaseEntry]` to `XCTMain` makes modern SwiftPM run zero tests; the runner now
  adds `--enable-test-discovery` (SWIFT-D042).
* SWIFT-D059: `validation/minimization-evidence/trigger.patch` was declared in
  `case.json` but missing from the repository. It was copied as text from the earlier
  validation tree and its sha256 matches the one recorded in `case.json`.
* `fetch_sources.py` retries a failed clone (default 5 attempts, set
  `D4X_CLONE_RETRIES`) and removes the partial `repo.git` between attempts.
  Without that cleanup a half-cloned directory is later treated as present.

## Files added from the earlier validation tree

* `cases/elixir/*/validation/excluded-tests.json` (100 files) and
  `metadata/excluded-tests-manifest.json`. Copied unchanged from the v1.1.3
  Elixir package that the earlier validation produced; the repository `case.json`
  files are byte-identical to that package's. The manifest total (1834 test
  identities, 44 cases with exclusions) equals the sum of the per-case files. For
  ELIXIR-001 the list equals the 14 failures seen in the fresh-host fixed run. The
  other cases were not compared that way: ELIXIR-036 and ELIXIR-084 were replayed
  with the check on and passed, the rest were not run.
* `d4x` now fails an Elixir fixed side if a failing test is not in that list, and
  records `exclusions_checked` in `result.json`. A case without the file is still
  judged by its trigger tests only.
* `metadata/r-environment-lock.json`. All 106 R environment files in the earlier
  tree have identical content, so one file serves every R case; the per-case
  `environment_file` paths in `case.json` still point at
  `framework/projects/*/environments/...`, which are not in this repository. Six
  absolute paths on the earlier server (`tools.*.path`) were removed. It lists 293
  entries for 288 package names: five base-R recommended packages (`codetools`,
  `lattice`, `MASS`, `rpart`, `survival`) appear twice with different versions.
  This is the lock as recorded; it was not re-derived.
* BENCH-1 was re-run after installing `glue 1.8.0` and `withr 3.0.2` to match the
  lock (the other direct dependencies already matched): buggy fails, fixed passes.
  Only BENCH-1's direct dependencies were compared; 206 of the 288 locked packages
  are not installed on the test host and were not needed for that case.

## Limits of these checks

* The Elixir verdict now also checks remaining failures against
  `validation/excluded-tests.json`. Only ELIXIR-001, 036 and 084 were run with that
  check; the listed failures were reproduced in the earlier validation, not re-derived here.
* The Swift images are rebuilt, so their digests differ from the originals. The
  runtime versions match, but that does not show the images are equivalent.
* The earlier validation tree sets `D4X_ENABLE_XCTEST=1` for SWIFT-D052 and D059 and
  `-Xlinker -Bsymbolic` for D074/D075. This runner does not set the first; both D052 and
  D059 pass without it.
* SWIFT-D058's trigger is a compile error (`compile::Tests/...:151:13`). The
  fixed side passes when the test target compiles, and the log shows
  `No matching test cases were run`. The runner still judges by exit code and
  does not check that the buggy-side error is at the expected location.
* `env/r.md` refers to `framework/projects/Bench/environments/*.json`, which is
  still not in the repository; `metadata/r-environment-lock.json` is the same
  content in one file. BENCH-1 passes with its direct dependencies at the locked
  versions; no other R case was run.
* `oracle.jsonl` marks these cases `DECLARED`. These runs are a first
  independent replay of one case per language, not a clean-room release gate.

## Toolchain commands used

```bash
sudo apt-get install -y build-essential unzip git curl python3
sudo apt-get install -y lua5.4 liblua5.4-dev luarocks && sudo luarocks install busted 2.2.0-1
sudo apt-get install -y cpanminus make                      # Perl
sudo apt-get install -y openjdk-17-jdk-headless             # Kotlin (JDK 17 cases)
sudo apt-get install -y docker.io docker-buildx             # Elixir / Swift
```

R 4.4.3 is not in Ubuntu 24.04's archive (it has 4.3.3). Posit's build works:

```bash
curl -fL -o /tmp/r443.deb https://cdn.posit.co/r/ubuntu-2404/pkgs/r-4.4.3_1_amd64.deb
sudo apt-get install -y /tmp/r443.deb gfortran libcurl4-openssl-dev libssl-dev libxml2-dev
export PATH=/opt/R/4.4.3/bin:$PATH R_LIBS=$HOME/d4x/Rlib
```

Dart, Julia and the JDK are chosen per case from `language_version` /
`build.julia_version` / `java_version`. Do not install one global version.

## Practical notes

* Long builds (Julia, Kotlin, Docker) exceed typical SSH command limits. Run
  them with `nohup` and poll.
* Kotlin used about 6 of 7 GB RAM during the first Gradle build.
* `images/build/*/Dockerfile` start with `# syntax=docker/dockerfile:1.7`. That
  makes BuildKit pull the `docker/dockerfile` frontend from Docker Hub first. The
  Dockerfiles use no heredoc or `--mount`, so on hosts that cannot reach it the
  first line can be dropped for a build.
* The README quick start uses `python`; Ubuntu 24.04 only provides `python3`.
