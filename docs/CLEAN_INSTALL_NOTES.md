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
| Swift | SWIFT-D058 | PASS | image rebuilt with `images/build`; trigger is a compile error |
| ArkTS | - | not run | needs a device or emulator |

Not covered: the 56 Swift cases that ship a `dependency_cache` (the largest
group totals about 30 GB of external assets), and four of the five Swift image
tags (only `5.10.1-restored-20260908` was built).

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
* `fetch_sources.py` retries a failed clone (default 5 attempts, set
  `D4X_CLONE_RETRIES`) and removes the partial `repo.git` between attempts.
  Without that cleanup a half-cloned directory is later treated as present.

## Limits of these checks

* The Elixir verdict is looser than `canonical_test_policy`. That policy also
  requires every other failure to be listed in `validation/excluded-tests.json`,
  and that file is not in this repository, so it was not checked.
* SWIFT-D058's trigger is a compile error (`compile::Tests/...:151:13`). The
  fixed side passes when the test target compiles, and the log shows
  `No matching test cases were run`. The runner still judges by exit code and
  does not check that the buggy-side error is at the expected location.
* `env/r.md` refers to `framework/projects/Bench/environments/*.json`, which is
  not in the repository, so the 14 pinned R package versions cannot be read.
  BENCH-1 passed on the latest packages, which does not show it passes on the
  pinned ones.
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
