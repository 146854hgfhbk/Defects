# Second-host replay: why 350 cases were not all PASS

An audit replayed the Kotlin, Elixir, Swift and ArkTS cases (350 in total) on a second host and
applied a strict gate: **the declared trigger fails on the buggy side and the whole test suite
passes on the fixed side.** This note explains each non-PASS result, says which causes lie in the
host and which in the dataset, and records what was re-checked on the clean replay host afterwards.

* Audit date: 2026-11-01. Repository commit: `2f0f15ecad25b0a81abbb687b66dbbb3b287b87f`, with
  `scripts/d4x.py` as in that commit. Which `D4X_*` options the audit batch used is not recorded in
  the report or in the per-case `result.json` files (they hold only `mode: local`).
* Oracle level: `DECLARED`. The audit checks the differential declared in the repository. It does
  not claim compatibility with the official Defects4J CLI, an independent semantic oracle, or
  reproducibility on an arbitrary network-restricted host.
* Re-check host: the clean Ubuntu 24.04 host used for the other replay notes (2 vCPU, 7 GB RAM,
  Docker), with the same `scripts/d4x.py`.

## Result of the audit

| Language | Cases | PASS | FAIL | BLOCKED |
|---|---:|---:|---:|---:|
| Kotlin | 100 | 66 | 7 | 27 |
| Elixir | 100 | 98 | 2 | 0 |
| Swift | 100 | 99 | 0 | 1 |
| ArkTS | 50 | 0 | 0 | 50 |
| Total | 350 | 263 | 9 | 78 |

Elixir and Swift include follow-up runs made after the first pass: ELIXIR-100 (first BLOCKED) and
SWIFT-D018 (first FAIL) were repeated and counted as PASS in the table above.

## Why 87 results are not PASS

The 87 are the 9 FAIL and 78 BLOCKED results in the table above.

| Cause | Cases | Count | Where the cause lies |
|---|---|---:|---|
| The audit host could not download the Gradle distribution (`Connect timed out` in `org.gradle.wrapper.Download`) | KOTLIN-107, 124, 141, 142, 145, 146, 147, 149, 151, 160, 161, 164, 167, 173, 176, 177, 196, 197, 198, 200, 204, 205, 207, 227 | 24 | host network |
| Gradle daemon died during the build | KOTLIN-208 | 1 | host resources (not confirmed) |
| A Gradle task failed; the log excerpt does not show why | KOTLIN-162, 186 | 2 | not determined by the audit |
| Tests that are not the trigger fail on the fixed side | KOTLIN-152, 153, 155, 158, 159, 170; ELIXIR-017, 081 | 8 | unrelated or unstable tests |
| PDF trigger fails on both sides, and a network test fails on the fixed side | KOTLIN-501 | 1 | toolchain setup and network |
| A dependency requires `swift-tools-version: 6.2`, the host had Swift 6.1.3 | SWIFT-D031 | 1 | dependency resolution (see below) |
| No OpenHarmony SDK, `hvigor`, `hdc`, device or emulator, or signing material | ARKTS-001 to 050 | 50 | needs a device |

The Kotlin BLOCKED rows add up to the 27 (24 + 1 + 2). Two further cases were not PASS on the first
pass and are counted as PASS in the table above because the audit repeated them: SWIFT-D018
(container file-descriptor limit, described below) and ELIXIR-100 (Hex bootstrap, described below).

### Network: 24 Kotlin cases

The first Gradle call in each case uses the project's wrapper, which fetches
`https://services.gradle.org/distributions/gradle-<version>-all.zip`. On the audit host that
download timed out on at least one side of each of these cases. The case data is not involved: the
failure happens before any project code is compiled. Pre-populating
`GRADLE_USER_HOME/wrapper/dists` or giving the host a route to the download site removes it.

In 8 of the 24 (KOTLIN-124, 147, 149, 151, 173, 197, 198, 207) the fixed side compiled and the buggy
side did not. The same host therefore completed the download once and failed it another time, which
points to unstable connectivity and not to a permanent block. Neither side can be judged when the
download fails, so the case is BLOCKED and not FAIL.

### Tests that are not the trigger: 8 cases

In these cases the trigger test behaves as declared (fails on buggy, passes on fixed), but the fixed
side's whole suite has failures that are not on the case's exclusion list, so the strict gate rejects
the case.

| Case | Failing on the fixed side in the audit | Also failing on the buggy side |
|---|---|---|
| KOTLIN-152 | `GrazieInspectionTest.testGerman` | no |
| KOTLIN-153 | `GrazieInspectionTest.testGerman` | no |
| KOTLIN-155 | `GrazieInspectionTest`: `testGerman`, `testGermanCommandSpacing`, `testGermanList` | yes (same three) |
| KOTLIN-158 | `LatestTexifyVersionTest.testVersion` | yes |
| KOTLIN-159 | `GrazieInspectionTest`: `testTabular`, `testGermanGlossaries`, `testGermanCommandSpacing`; `LatestTexifyVersionTest.testVersion` | no (it fails two other tests) |
| KOTLIN-170 | `JsonSchemaTest`: 3 tests | yes (same three) |
| ELIXIR-017 | `AshGraphql.RelationshipPaginationTest` "works when nested on return values for update mutations" | no |
| ELIXIR-081 | `ReverseProxyPlugTest` "can be initialised as a plug with an MFA error callback" | no |

What the audit data shows: the Grazie tests that fail differ between cases of the same project
(KOTLIN-155 fails `testGerman`, `testGermanCommandSpacing`, `testGermanList`; KOTLIN-159 fails
`testTabular`, `testGermanGlossaries`, `testGermanCommandSpacing`), and in KOTLIN-155, 158 and 170 the
same tests fail on the buggy side too, so those failures do not depend on the fix. The test sources
were not read, so no claim is made about why they fail.

### KOTLIN-501

The PDF tests need Node, Puppeteer and Chrome. In the audit's trigger-only run, the trigger
`CompileCommandTest > pdf with toc and id starting with digit` failed on **both** sides, so no
differential was observed. In the full run the buggy side failed as expected and the fixed side
failed `MediaStorageTest.media storage` with a network timeout. The audit host installed a separate
Node 20.20.2, Puppeteer 24.43.1 and Chrome for Testing 151 sidecar for this case.
`NodeNpmWrapperTest` asserts that Puppeteer is *not* linked, so a pre-installed copy can fail that
test; whether it did here was not checked. See `env/kotlin.md` for the setup that was used on the
clean replay host.

### Swift

* SWIFT-D018: the fixed run died in `swift test` with `epoll_create(size:): Too many open files
  (errno: 24)`. The audit repeated it with the container's `nofile` limit raised to 65536 and it
  passed. A host or Docker default that is lower than the image needs causes this.
* SWIFT-D031: a dependency declared `swift-tools-version: 6.2` and the host had Swift 6.1.3. The case
  declares the 6.1 image. The recorded `Package.resolved` pins `swift-syntax` to a commit on `main`,
  `d769922`. A resolve that does not start from the recorded file would take the current tip of
  `main`, which can need a newer toolchain. This explanation was not reproduced.

### Elixir

* ELIXIR-100: `mix local.hex --force` failed with `builds.hex.pm` DNS `nxdomain`. The audit reused
  cached dependencies for the repeat. The dependency step needs network (`D4X_CONTAINER_NET=1`).
* ELIXIR-017 and 081: see the table above.

### ArkTS

All 50 cases need an OpenHarmony SDK, `hvigor`, `hdc`, an authorized device or emulator, and signing
material. None of these is available on the audit host or the clean replay host (no KVM). They stay
`DEVICE_REQUIRED/NOT_RUN`; no result is claimed.

## Two criteria

`scripts/d4x.py` judges a case by its declared trigger tests, and for some cases it also checks the
remaining failures against `validation/excluded-tests.json`. The audit's strict gate additionally
requires every test on the fixed side to pass. The two are not the same, and the difference is
what turns the eight cases above into FAIL: under the `d4x` criterion their trigger differential is
already the declared one.

Neither criterion is wrong. They answer different questions: "does the declared trigger separate
the two sides" and "is the fixed side clean". A case that passes the first and not the second has
unrelated or unstable tests in its project, and the exclusion list is the place where those are
recorded.

## Re-check on the clean replay host

Each case was run once with `scripts/d4x.py` from commit `2f0f15e`, unchanged. The options column lists the
`D4X_*` settings used, as documented in `docs/REPLAY_KOTLIN_ELIXIR.md`. Every Kotlin run also used
`--timeout 5400` (the default is 1800 s), the JDK named in `build.java_version`, and the Gradle proxy settings in
`gradle.properties`. ARKTS cases are not listed (no device).

12 of 39 cases were re-run; 27 were not.

| Case | Audit result | Clean host, this re-run | Options | Time |
|---|---|---|---|---:|
| ELIXIR-017 | FAIL | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 874s |
| ELIXIR-081 | FAIL | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 283s |
| ELIXIR-100 | BLOCKED first, then PASS | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 246s |
| KOTLIN-107 | BLOCKED | not re-run | | |
| KOTLIN-124 | BLOCKED | not re-run | | |
| KOTLIN-141 | BLOCKED | not re-run | | |
| KOTLIN-142 | BLOCKED | not re-run | | |
| KOTLIN-145 | BLOCKED | not re-run | | |
| KOTLIN-146 | BLOCKED | not re-run | | |
| KOTLIN-147 | BLOCKED | not re-run | | |
| KOTLIN-149 | BLOCKED | not re-run | | |
| KOTLIN-151 | BLOCKED | not re-run | | |
| KOTLIN-152 | FAIL | PASS | none | 669s |
| KOTLIN-153 | FAIL | PASS | none | 708s |
| KOTLIN-155 | FAIL | PASS | none | 819s |
| KOTLIN-158 | FAIL | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 1032s |
| KOTLIN-159 | FAIL | PASS | none | 1480s |
| KOTLIN-160 | BLOCKED | not re-run | | |
| KOTLIN-161 | BLOCKED | not re-run | | |
| KOTLIN-162 | BLOCKED | not re-run | | |
| KOTLIN-164 | BLOCKED | not re-run | | |
| KOTLIN-167 | BLOCKED | not re-run | | |
| KOTLIN-170 | FAIL | PASS | none | 269s |
| KOTLIN-173 | BLOCKED | not re-run | | |
| KOTLIN-176 | BLOCKED | not re-run | | |
| KOTLIN-177 | BLOCKED | not re-run | | |
| KOTLIN-186 | BLOCKED | not re-run | | |
| KOTLIN-196 | BLOCKED | not re-run | | |
| KOTLIN-197 | BLOCKED | not re-run | | |
| KOTLIN-198 | BLOCKED | not re-run | | |
| KOTLIN-200 | BLOCKED | not re-run | | |
| KOTLIN-204 | BLOCKED | not re-run | | |
| KOTLIN-205 | BLOCKED | not re-run | | |
| KOTLIN-207 | BLOCKED | not re-run | | |
| KOTLIN-208 | BLOCKED | not re-run | | |
| KOTLIN-227 | BLOCKED | not re-run | | |
| KOTLIN-501 | FAIL | PASS | none; Node 20 on PATH, Puppeteer not pre-installed, Chrome via a `--no-sandbox` wrapper | 1010s |
| SWIFT-D018 | FAIL first, then PASS | PASS | recorded Package.resolved, then offline |  |
| SWIFT-D031 | BLOCKED | PASS | recorded Package.resolved, then offline |  |

### Reading of the re-check

* **The nine FAIL results did not reproduce.** KOTLIN-152, 153, 155, 158, 159, 170 and 501 and ELIXIR-017
  and 081 all passed on the clean host: the trigger fails on the buggy side and the whole fixed-side
  suite passes. One run of each case does not show that an unstable test is stable, but it does show that
  these cases are not stably failing on the fixed side.
* **SWIFT-D031 passes** on the 6.1 image when the recorded `Package.resolved` is in place before the
  resolve. **SWIFT-D018 passes** without raising the file-descriptor limit.
* **ELIXIR-100 passes** when the dependency step has network access.
* **The BLOCKED Kotlin cases** are the ones that depend on the host reaching the Gradle download site.
  Their re-run was still in progress when this note was written; a row that says "not re-run" has no
  result from this re-check, in either direction.

## What a reader needs to reproduce these cases

* **Network.** The host must reach `services.gradle.org` (or have `GRADLE_USER_HOME` pre-populated),
  the Maven and Gradle plugin repositories, `github.com`, a Docker registry, `builds.hex.pm` and
  `repo.hex.pm`, and the SwiftPM package hosts. A dependency step that times out ends as BLOCKED,
  not as a result about the case.
* **Memory.** Gradle builds of the large projects (TeXiFy, ORT, KOTLIN-155, 170) need several GB; one
  Gradle daemon was killed during the audit (KOTLIN-208). Run them one at a time.
* **File descriptors.** If `swift test` dies with `Too many open files`, start the container with
  `--ulimit nofile=65536:65536`.
* **Options.** Several Kotlin and Elixir cases need `D4X_*` options; they are listed in
  `docs/REPLAY_KOTLIN_ELIXIR.md`. A run without them is not a failed case.
* **Online tests.** Some tests in the upstream projects reach the network (Grazie, the version lookup in
  `LatestTexifyVersionTest`, `MediaStorageTest`, `hub.docker.com` in a Phoenix test). Under
  `--network none` or behind a restricted network they can fail on the fixed side.

## What this note does not show

* It does not show that every BLOCKED result would pass: only the cases listed in the table above were
  re-run on the clean host.
* It does not show that the unrelated failing tests are harmless for every use of the dataset. They are
  failures in the upstream project's own suite on the fixed revision.
* The audit and the re-check are single runs of each case.
