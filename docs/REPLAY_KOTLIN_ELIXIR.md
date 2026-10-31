# Replay notes: Kotlin and Elixir (clean server, 2026-10-28)

Result on one clean Ubuntu 24.04 server (2 vCPU, JDK 8/11/17/21/25, Android SDK 34, Docker):

| Language | Cases | PASS | How it was measured |
|---|---:|---:|---|
| Kotlin | 100 | 100 | latest result per case from several runs, with the `D4X_KOTLIN_*` switches below |
| Elixir | 100 | 100 | latest result per case from several runs; 042 and 051 re-checked three times each with `D4X_ELIXIR_RERUN_FAILED=3` |

This is not one final full run with a single d4x version. Every result below that needed a
switch is a d4x-derived result, not the dataset's own declared command.

## Kotlin

### Setup

* JDK 8, 11, 17, 21 and 25 side by side; set `JAVA_HOME` and `PATH` per case from
  `build.java_version` before `d4x run` (`d4x` does not choose it). Gradle comes from each
  checkout's wrapper.
* Android SDK 34 (build-tools 34.0.0) in `$HOME/d4x/android-sdk` for KOTLIN-001 and 120 to 123.
* Proxy settings go in `gradle.properties`, not `JAVA_TOOL_OPTIONS` (see `env/kotlin.md`).
* Memory: the first Gradle build used about 6 of 7 GB. Run Kotlin cases one at a time. The large
  builds (TeXiFy-IDEA, KOTLIN-155) pushed the load average to 62 and made SSH unresponsive for
  about 40 minutes; limit them with `org.gradle.workers.max=1`, `-Xmx2g` and `nice`.
* Single cases take about 2 to 9 minutes; the large ones take far longer (see the timeout row below).

### Handled by `d4x` without an option

* 68 cases have `revision_mode = base_plus_gold_patch`: `fixed_revision` does not exist upstream, so
  the fixed side is `buggy_revision` plus the trigger and production patches.
* 7 trigger patches with CRLF line endings are normalised before they are applied.
* `.\gradlew.bat` in 88 cases is run as `./gradlew`.
* Android modules use their own `compile_task` / `test_task`.

### Causes and options

Causes found in the logs, and what fixed each:

| Cause | Cases | Fix |
|---|---|---|
| `minimized-source.patch` dropped a helper function or import that the kept lines still use, so the fixed side does not compile | 26 (e.g. 133, 144, 158, 160, 162, 172-197) | `D4X_KOTLIN_ORIGINAL_SOURCE=1` applies `original-source.patch` instead |
| 1800 s default command timeout; large builds (TeXiFy, ORT) need 35 min to compile | 156, 164, 165, 167 | `scripts/d4x.py run ... --timeout 5400` |
| network reset while fetching git objects or Gradle artifacts | 158, 159, 160, 161, 195 | rerun |
| `case.json` runs `:ktlint-rule-engine:test` but the trigger tests are in `ktlint-ruleset-standard` | 191, 202 | `D4X_KOTLIN_DECLARED_TASKS=1` uses the declared `compile_task` / `test_task` |
| aggregate `gradlew test` stops at the first failing module, so later modules (with the trigger tests) never run | 164, 165, 167 | `D4X_KOTLIN_CONTINUE=1` adds `--continue` |
| trigger tests call API that the fix introduces (`hasModifier`, `lineLength`), so the buggy tree cannot compile them | 189, 194 | `D4X_KOTLIN_RETAIN_API=1` applies `patches/buggy-retained-api.json` (the diff of one file, additive declarations only) to the buggy side |
| `jcenter`-era plugin dependencies are gone from the public repositories | 227 | a fallback repository in a Gradle init script, and no Gradle proxy for `plugins-artifacts.gradle.org` |
| PDF tests need Node 20, Puppeteer and Chrome | 501 | Node 20.20.2; Puppeteer is installed by the test itself with `npm` (do **not** pre-install it: `NodeNpmWrapperTest` asserts it is not linked); Chrome 148 launched with `--no-sandbox` |

Unrelated failing tests on the fixed side (`validation/excluded-tests.json`):

* KOTLIN-164: 1 test (`FileUtilsTest searchUpwardFor`)
* KOTLIN-165: 2 tests (same, and `SpringPackageCurationProviderTest`)
* KOTLIN-167: 8 tests (4 `CarthageTest`, 2 `VersionControlSystemTest`, `ExtensionsTest`, and a
  `ClearlyDefinedPackageCurationProviderTest` that calls an online service)

These were observed on the clean server. They were not run against the upstream GOLD fix.
With a list present, `d4x` accepts a non-zero Gradle exit on the fixed side only if every failed
test is on the list, the failure count matches Gradle's summary, and every trigger test class was
seen passing.

## Elixir

### Setup

* Docker, with the case images pulled by digest from `images/manifest.json`, or built from
  `images/build/`. Each image is 1.2 to 1.5 GB and Docker Hub pulls can fail midway; retry.
* `D4X_CONTAINER_NET=1`: the compile and `mix deps.get` step runs on the host network (set
  `https_proxy` if needed); the test step always runs with `--network none`.
* ELIXIR-036 needs a network `mix deps.get` before the offline run (about 335 MB of git
  dependencies).
* `D4X_ELIXIR_COMPILE_ENV=test` compiles in `MIX_ENV=test`. ELIXIR-086 needs it: the default `dev`
  compile also builds `only: :dev` dependencies, and `earmark` 1.2.2 does not compile on
  Elixir 1.16.
* The verdict comes from the named trigger tests and the case's `validation/excluded-tests.json`.
  A trigger written as `path:line` (ELIXIR-027, 030, 061, 099) is matched by `d4x`.

### Flaky suites

ELIXIR-051: `WebSocketChannelsTest` restarts its endpoint on the fixed port 5807 in every test.
When the previous listener is not yet released, a different test dies with `:eaddrinuse` in each
run (nine runs, nine different tests). `--seed 0` and `--max-cases 1` did not remove it.
`D4X_ELIXIR_RERUN_FAILED=n` reruns only the failed tests (`mix test --failed`) up to n times on
the fixed side; a test that still fails stays a failure. The first run's log is kept as
`fixed-test.log`, the reruns as `fixed-test-rerun<i>.log`, and `result.json` lists
`flaky_recovered` and `reruns`. The trigger tests must pass in the first run; a rerun never
rescues a trigger test.

Checks with the case's own exclusion list (3 entries, no observed-flaky entries):

* ELIXIR-051: 3 of 3 runs PASS with `D4X_ELIXIR_RERUN_FAILED=3`
* ELIXIR-042: 3 of 3 runs PASS with `D4X_ELIXIR_RERUN_FAILED=3` (the list has 1 entry)

Three `Mix.Tasks.Phx.Gen.ReleaseTest` tests call `hub.docker.com`; they fail under
`--network none` and are on the case's list.

`D4X_ELIXIR_SEED=<n>` (fixed ExUnit seed) and `D4X_ELIXIR_MAX_CASES=<n>` (`--max-cases`) are also
available. They are d4x options, not part of the dataset. ELIXIR-053, 059, 064, 065 and 066
passed in their latest run with `D4X_ELIXIR_SEED=0` (order-dependent suites); they have not been
rechecked with the rerun option.
