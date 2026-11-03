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
failure happens before any project code is compiled.

The request does not end at `services.gradle.org`. It is redirected through `github.com` to
`release-assets.githubusercontent.com`, and that host did not answer from the audit host when it was
checked later (see "Re-run on the audit host"). Making `services.gradle.org` reachable is therefore not
enough, and neither is a pre-populated `GRADLE_USER_HOME/wrapper/dists` unless it survives Gradle's cache
cleanup (same section).

In 8 of the 24 (KOTLIN-124, 147, 149, 151, 173, 197, 198, 207) the fixed side compiled and the buggy side did
not. Both sides use the same distribution, so something changed between the two downloads. The audit report
says that Gradle wrappers were installed for the blocked cases, which would explain it; that was not checked.
Neither side can be judged when the download fails, so the case is BLOCKED and not FAIL.

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
`NodeNpmWrapperTest` asserts that Puppeteer is *not* linked; in the later pass on this host a global
Puppeteer did not make it fail. See `env/kotlin.md` for the setup and for what stops Chrome from
starting.

### Swift

* SWIFT-D018: the fixed run died in `swift test` with `epoll_create(size:): Too many open files
  (errno: 24)`. The audit repeated it with the container's `nofile` limit raised to 65536 and it
  passed. A host or Docker default that is lower than the image needs causes this. The runner now sets
  the limit itself (see "Runner changes" below).
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

## The criterion

The audit's gate is strict: **the declared trigger fails on the buggy side, and the whole test suite
passes on the fixed side.** `scripts/d4x.py` is looser in two ways: it judges most languages by the
declared trigger tests, and for some cases it accepts fixed-side failures that are listed in
`validation/excluded-tests.json`. Under the strict gate the eight cases above are FAIL, because the
fixed side's suite has failures that are not on any list.

A case that passes the trigger check and not the strict one has unrelated or unstable tests in its
project. The exclusion list is where those are recorded; it is a judgement made case by case, not
something the runner should add on its own.

## Re-check on the clean replay host

Each case was run once with `scripts/d4x.py` from commit `2f0f15e`, unchanged. The options column lists the
`D4X_*` settings used, as documented in `docs/REPLAY_KOTLIN_ELIXIR.md`. Every Kotlin run also used
`--timeout 5400` (the default is 1800 s), the JDK named in `build.java_version`, and the Gradle proxy settings in
`gradle.properties`. ARKTS cases are not listed (no device).

39 of 39 cases were re-run; 0 were not.

| Case | Audit result | Clean host, this re-run | Options | Time |
|---|---|---|---|---:|
| ELIXIR-017 | FAIL | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 874s |
| ELIXIR-081 | FAIL | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 283s |
| ELIXIR-100 | BLOCKED first, then PASS | PASS | D4X_CONTAINER_NET=1, D4X_ELIXIR_RERUN_FAILED=3 | 246s |
| KOTLIN-107 | BLOCKED | PASS | none | 184s |
| KOTLIN-124 | BLOCKED | PASS | none | 363s |
| KOTLIN-141 | BLOCKED | PASS | none | 189s |
| KOTLIN-142 | BLOCKED | PASS | none | 182s |
| KOTLIN-145 | BLOCKED | PASS | none | 223s |
| KOTLIN-146 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 172s |
| KOTLIN-147 | BLOCKED | PASS | none | 165s |
| KOTLIN-149 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 185s |
| KOTLIN-151 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 101s |
| KOTLIN-152 | FAIL | PASS | none | 669s |
| KOTLIN-153 | FAIL | PASS | none | 708s |
| KOTLIN-155 | FAIL | PASS | none | 819s |
| KOTLIN-158 | FAIL | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 1032s |
| KOTLIN-159 | FAIL | PASS | none | 1480s |
| KOTLIN-160 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 1324s |
| KOTLIN-161 | BLOCKED | PASS | none | 698s |
| KOTLIN-162 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 683s |
| KOTLIN-164 | BLOCKED | PASS | D4X_KOTLIN_CONTINUE=1; fixed suite exits 1, accepted through validation/excluded-tests.json | 1695s |
| KOTLIN-167 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1, D4X_KOTLIN_CONTINUE=1; fixed suite exits 1, accepted through validation/excluded-tests.json | 1382s |
| KOTLIN-170 | FAIL | PASS | none | 269s |
| KOTLIN-173 | BLOCKED | PASS | none | 108s |
| KOTLIN-176 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 113s |
| KOTLIN-177 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 97s |
| KOTLIN-186 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 106s |
| KOTLIN-196 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 98s |
| KOTLIN-197 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 93s |
| KOTLIN-198 | BLOCKED | PASS | none | 111s |
| KOTLIN-200 | BLOCKED | PASS | none | 151s |
| KOTLIN-204 | BLOCKED | PASS | none | 129s |
| KOTLIN-205 | BLOCKED | PASS | D4X_KOTLIN_ORIGINAL_SOURCE=1 | 111s |
| KOTLIN-207 | BLOCKED | PASS | none | 139s |
| KOTLIN-208 | BLOCKED | PASS | none | 297s |
| KOTLIN-227 | BLOCKED | PASS | no Gradle proxy; fallback `jcenter` repository init script during the run | 284s |
| KOTLIN-501 | FAIL | PASS | none; Node 20 on PATH, Puppeteer not pre-installed, Chrome via a `--no-sandbox` wrapper | 1010s |
| SWIFT-D018 | FAIL first, then PASS | PASS | recorded Package.resolved, then offline; whole fixed suite also run without --filter: exit 0 |  |
| SWIFT-D031 | BLOCKED | PASS | recorded Package.resolved, then offline; whole fixed suite also run without --filter: exit 0 |  |

### Reading of the re-check

* **The nine FAIL results did not reproduce.** KOTLIN-152, 153, 155, 158, 159, 170 and 501 and ELIXIR-017
  and 081 all passed on the clean host: the trigger fails on the buggy side and the whole fixed-side
  suite passes. One run of each case does not show that an unstable test is stable, but it does show that
  these cases are not stably failing on the fixed side.
* **SWIFT-D031 passes** on the 6.1 image when the recorded `Package.resolved` is in place before the
  resolve. **SWIFT-D018 passes** without raising the file-descriptor limit.
* **ELIXIR-100 passes** when the dependency step has network access.
* **All 27 BLOCKED Kotlin cases pass** on the clean host, which can reach the Gradle download site.
  This includes KOTLIN-208, where the audit's Gradle daemon had died, and KOTLIN-162 and 186, where the
  audit log does not show why a Gradle task failed. 162 and 186 passed with
  `D4X_KOTLIN_ORIGINAL_SOURCE=1`; whether the audit run lacked that option is not known.
* **Some cases need an option or a special setup even with network access**, as the options column
  shows: `D4X_KOTLIN_ORIGINAL_SOURCE=1` for 11 of the 27 re-run Kotlin cases (and 158), `--continue` for
  164 and 167, and for KOTLIN-227 a Gradle run without the proxy plus a fallback repository for
  `jcenter`-era artifacts that no longer exist in the public repositories. A reader who only fixes the
  network will still need these.

## Re-run on the audit host

The audit host was used again, after the changes described under "Runner changes", with a fresh checkout of
this repository, JDK 8, 11, 17, 21 and 25, and no proxy. 32 of the 34 Kotlin cases that were not PASS in the
audit were re-run on it; KOTLIN-227 and 501 were not. KOTLIN-120 was not in the audit and was not run on it
either.

| Result on the audit host | Cases | Count |
|---|---|---:|
| PASS, fixed-side test command exits 0 | 107, 124, 141, 142, 145, 146, 147, 149, 151, 155, 158, 173, 176, 177, 186, 196, 197, 198, 200, 204, 205, 207, 208 | 23 |
| BLOCKED: the build reads `raw.githubusercontent.com` | 160, 161, 162 | 3 |
| FAIL: `JsonSchemaTest` on the fixed side | 164, 167, 170 | 3 |
| FAIL: `LatestTexifyVersionTest` on the fixed side | 152, 153 | 2 |
| FAIL: Grazie language-bundle tests on the fixed side | 159 | 1 |

On the same host and the same checkout, ELIXIR-017, 081 and 100 and SWIFT-D018 and D031 also pass. For
Elixir the proxy variables were unset and `D4X_CONTAINER_NET=1` was set, and the fixed-side suites had 189,
106 and 265 doctests plus 655 tests, all with 0 failures. ELIXIR-100 had `patches/compat.patch` applied on
both sides by the runner. For Swift the whole fixed suite was run offline in the case's image: D018 exits 1
with `epoll_create(size:): Too many open files` under the host's default limit of 1024 and exits 0 with
`--ulimit nofile=65536:65536`; D031 exits 0 in both.

For the 9 results that are not PASS, the evidence points at the host's network in every case, and at nothing
in the case data. For 6 of them the cause was read from the logs or the source; for the 3 ORT cases it is the
likely cause and not a confirmed one:

* **`*.githubusercontent.com` is unreachable from this host** (`raw`, `release-assets` and `objects` all time
  out), while `github.com`, `codeload.github.com` and the directory pages of `services.gradle.org` answer.
  A Gradle distribution is not served by `services.gradle.org`: the request is redirected
  (`307`, then `302`) through `github.com` to `release-assets.githubusercontent.com`. Probing the small
  `.sha256` file or the directory page therefore looks healthy while the real download times out. Probe the
  distribution URL itself, for example `curl -sSIL https://services.gradle.org/distributions/gradle-8.6-all.zip`.
* **DataFrame (160, 161, 162)**: `:core:generateDataFrameRepository` reads
  `https://raw.githubusercontent.com/Kotlin/dataframe/master/data/jetbrains_repositories.csv` while it
  builds. The build fails with `Error while reading dataframe from data at ...` on both sides.
* **ORT (164, 167, 170)**: the repository-configuration schema that `JsonSchemaTest` loads contains `$ref`
  entries that point at `https://raw.githubusercontent.com/oss-review-toolkit/ort/main/integrations/schemas/`.
  Confirmed in a later pass: the test report says `Failed to load json schema from
  https://raw.githubusercontent.com/oss-review-toolkit/ort/main/integrations/schemas/resolutions-schema.json`
  (and the same for `package-configurations`); 13 of the 16 example files validated, the other 3 could not
  load their schema.
* **TeXiFy (152, 153)**: the only fixed-side failure is `LatestTexifyVersionTest > testVersion`. The test
  calls `LatexErrorReportSubmitter.getLatestVersion()`, which does an HTTP GET with a connect and read timeout
  of 1000 ms and, on a timeout, returns an empty object, so the assertion that the version is not blank fails.
* **TeXiFy (159)**: the fixed-side failures are `GrazieInspectionTest` tests; the stack shows
  `LangDownloader.promptToSelectLanguageBundleManually`, that is, the test tried to download a language bundle.

All of these cases passed on the clean replay host, with 164 and 167 passing only through their exclusion
lists. The audit host and the clean host differ in whether they can reach the hosts above, and in nothing
the dataset controls.

### Third pass on the audit host

A third pass used the repository at the commit that contains the runner changes (`9f75cdf`), run from a
private directory with its own Gradle home. It covers the cases listed in a later report from the same host.

| Case | Result | Note |
|---|---|---|
| KOTLIN-153, 155, 157, 158 | PASS, fixed-side test command exits 0 | 158 with `D4X_KOTLIN_ORIGINAL_SOURCE=1` |
| KOTLIN-227 | PASS, exits 0 | needs Gradle 6.3, see below |
| KOTLIN-152 | FAIL on the fixed side | `GrazieInspectionTest > testGerman`: `Failed to download 'https://resources.jetbrains.com/grazie/model/language-tool/5.7/de-5.7.jar': Connect timed out` |
| KOTLIN-170 | FAIL on the fixed side | `JsonSchemaTest`, 3 tests: schema loaded from `raw.githubusercontent.com` |
| KOTLIN-167 | FAIL under the exclusion list | 3 failures not on the list: two `JsonSchemaTest` tests and one `ClearlyDefinedPackageCurationProviderTest` (an online service) |
| KOTLIN-501 | FAIL on the fixed side | `MediaStorageTest > media storage()`, `Connection reset`; buggy side fails the trigger as expected |
| ELIXIR-012 | PASS in 5 of 5 runs | the failures reported earlier did not appear |
| ELIXIR-086 | PASS in 9 of 10 runs | the 10th run failed with `StreamData.FilterTooNarrowError` (seed 62646) in a property test |
| SWIFT-D027, D031 | PASS | with step 1 of `REPLAY_SWIFT.md` (resolve with network, recorded `Package.resolved`) |

KOTLIN-152 failed a different network test here than on the clean host (`LatestTexifyVersionTest` there,
`GrazieInspectionTest` here): which network-dependent test fails varies from run to run.

**KOTLIN-501 without a working Chrome.** With the Chrome path pointing at a missing file, and with a real
Chrome that had no shared libraries and no `--no-sandbox`, the four PDF tests of `CompileCommandTest` failed on
the buggy and the fixed side alike, so the trigger could not separate them.

**KOTLIN-227 needs Gradle 6.3.** The case's wrapper asks for `gradle-6.3-all.zip`, which was not among the
distributions already cached on that host, and the download is the redirected one that the host cannot reach
(see "Network" above). The file was fetched from a mirror (`mirrors.cloud.tencent.com/gradle/`), its sha256
`0f316a67b971b7b571dac7215dcf2591a30994b3450e0629925ffcfe2c68cc5c` was compared with the value that
`services.gradle.org` publishes in `gradle-6.3-all.zip.sha256`, and it was unpacked into
`GRADLE_USER_HOME/wrapper/dists/gradle-6.3-all/<hash>/` with a `.ok` marker. The directory name is the
base-36 form of the MD5 of the distribution URL (`b4awcolw9l59x95tu1obfh9i8` for this URL). The case also
needs the `jcenter` fallback described in `docs/REPLAY_KOTLIN_ELIXIR.md`.

### The Gradle cache on the audit host

The first re-run ended mostly BLOCKED because each case tried to download its distribution. The
distributions were then copied into a private `GRADLE_USER_HOME/wrapper/dists`. During the run, four of the
copies lost their contents (an empty `.lck` and `.part` file were left) and the cases that needed them
timed out again. The Gradle documentation names the cause: cache cleanup checks the distributions in `wrapper/dists/` for
whether there is a corresponding `caches/<version>/` directory, and deletes the ones without. By default it
runs periodically (once every 24 hours), and with `--no-daemon` it runs in the foreground after the build
session. Every distribution that had a `caches/<version>/` directory survived; the four that were emptied
did not have one.

* The setting is not a property. It can only be set in an init script in `GRADLE_USER_HOME/init.d`, and the
  `caches { }` block exists only from Gradle 8.0, so the script must check the version:

```groovy
// GRADLE_USER_HOME/init.d/no-cache-cleanup.init.gradle
if (org.gradle.util.GradleVersion.current() >= org.gradle.util.GradleVersion.version("8.0")) {
    beforeSettings { settings ->
        settings.caches {
            cleanup = Cleanup.DISABLED
        }
    }
}
```

* After the script was in place, three distributions that no case uses (7.3, 7.4 and 7.4.2) were deleted
  again. Gradle 7.x builds were running at the time and cannot read the block above, so they are the likely
  cause; that was not confirmed. As a precaution, create an empty `caches/<version>/` directory for every
  distribution you keep, and restore a missing distribution before each case. With both in place no
  distribution was lost for the rest of the run.
* A complete entry holds `<name>.zip.ok` and the unpacked `gradle-<version>/`. The emptied entries held only
  `.lck` and `.part` files.

## The re-run checked against the strict gate

The `d4x` verdict in the table above is not the strict gate, so each of the 39 re-runs was checked
against it separately, from the stored `result.json` and the test logs.

* **37 of 39**: the fixed side's test command exited 0, with no exclusion list and no re-run of failed
  tests. For the three Elixir cases the logs show the whole suite: ELIXIR-017 189 tests, 081 106 tests,
  100 265 doctests and 655 tests, all with 0 failures.
* **KOTLIN-164 and 167**: the fixed side's command exits 1. They pass only through the case's
  `validation/excluded-tests.json` (1 and 7 listed failures, all observed on the clean host and not run
  against the upstream fix). They meet the strict gate only if you accept those lists.
* **SWIFT-D018 and D031**: the `d4x` run uses `swift test --filter <trigger>`, which is not the whole
  suite. The whole suite was therefore run separately on the fixed tree with no filter, offline, in the
  case's image. D018 ran 73 tests and D031 ran 63 (Swift Testing); both exited 0.

### KOTLIN-120

The second-host follow-up reported an unrelated failing test on the fixed side. It reproduced on the
clean host in one full run: the buggy side failed only the trigger
(`DeckPickerNoExternalFilesDirTest`), the fixed side failed `CardBrowserTest > FindReplace - replaces
text based on regular expression`, a UI assertion that looks for the text "1 note updated." and finds
no matching view. That test passes on the buggy side of the same run. Run alone on the unchanged fixed
tree, `CardBrowserTest` exited 0 in three of three repeats, and the trigger class run alone on the fixed
tree passes. The failure is therefore intermittent inside the full suite.

Decision: the test is recorded in `cases/kotlin/KOTLIN-120/validation/excluded-tests.json`, with the
classification `OBSERVED_NOT_GOLD_VERIFIED` (observed on the clean host, not run against the upstream
fix), like the lists for KOTLIN-164, 165 and 167. KOTLIN-120 meets the strict gate only through that list.

The same was done for the tests that need a network that the second host does not have: KOTLIN-501
(`MediaStorageTest`), KOTLIN-167 (three more entries and, after a second run, a fourth: the two ClearlyDefined
"existing curation" tests, two `JsonSchemaTest` tests) and KOTLIN-152 and 153 (`GrazieInspectionTest >
testGerman`, `LatestTexifyVersionTest > testVersion`). With the lists, real `d4x run`s on that host gave:
KOTLIN-501 PASS (buggy fails the trigger; the fixed side's only failure is the listed `MediaStorageTest`;
trigger confirmed by JUnit), KOTLIN-167 PASS (11 listed failures seen, none unlisted), KOTLIN-152 and 153
PASS (fixed suite exit 0, the network tests did not fail in that run). These pass the strict gate only
through the lists, or because the network happened to answer. KOTLIN-164 and 170 fail `JsonSchemaTest` for
the same reason and have no such entries.

A run of KOTLIN-501 made while four other cases were running failed the trigger itself
(`CompileCommandTest > pdf with toc and id starting with digit`, 33 s, `Expected value to be true`), where
the same case alone passes it in under 30 s for the whole class. Run the PDF case on an idle machine; a
trigger that fails because of load is not a candidate for an exclusion list.

On that host a connection to `raw.githubusercontent.com` either fails at once (`Connection reset`) or hangs in
`SYN-SENT` until the TCP connect times out, so the time a network test takes there varies by minutes.

The list alone was not enough. `d4x` required the Gradle log to show the trigger class as `PASSED`, and
AnkiDroid's log prints no passed tests; the class name was also taken as the text after the last dot of
the trigger name, which for a test with a display name is the whole sentence. See "Runner changes".

## Runner changes

`scripts/d4x.py` had three gaps that the second-host replay ran into. All three are fixed together with
this note:

* **Container proxy.** With `D4X_CONTAINER_NET=1` the proxy was hard-coded to `http://127.0.0.1:7890`
  and `https_proxy` was ignored. It is now taken from `D4X_PROXY` if that is set (an empty value means no
  proxy), else from `https_proxy` / `http_proxy` in the environment, else none.
* **`build_compatibility`.** The runner read only `patches.build_compatibility`. ELIXIR-100 declares it
  at the top level of `case.json`, so `patches/compat.patch` was not applied. The runner now reads both
  forms. ELIXIR-100 was re-run with the new runner: `compat.patch` is applied on both sides, the buggy
  side fails 1 test, and the fixed side passes 265 doctests and 655 tests.
* **Open-file limit.** Every container is now started with `--ulimit nofile=65536:65536`.

* **Exclusion check for Kotlin.** When the fixed side exits non-zero and the case has an exclusion list, the
  runner needs evidence that the trigger test passed. It looked only for `PASSED` lines in the Gradle log.
  It now also accepts the JUnit XML named by `build.test_results_glob`: every trigger test must have a
  `<testcase>` with no `<failure>`, `<error>` or `<skipped>`. The XML is used only when it shows the trigger
  passing; otherwise the old check applies, so KOTLIN-164 and 167 are judged as before. This is what lets
  the KOTLIN-120 list take effect.

The first three changes touch 21 lines. Other languages do not use containers, so their runs are not affected.
ELIXIR-001 and 081 were re-run with the new runner and still pass.

## What a reader needs to reproduce these cases

* **Network.** The host must reach `services.gradle.org` and the GitHub hosts that Gradle distributions are
  redirected to (`github.com` and `release-assets.githubusercontent.com`), and `raw.githubusercontent.com`
  (DataFrame and ORT read files from it), or have `GRADLE_USER_HOME` pre-populated as described above. It must
  also reach the Maven and Gradle plugin repositories, a Docker registry, `builds.hex.pm` and `repo.hex.pm`,
  and the SwiftPM package hosts. A dependency step that times out ends as BLOCKED,
  not as a result about the case.
* **Memory.** Gradle builds of the large projects (TeXiFy, ORT, KOTLIN-155, 170) need several GB; one
  Gradle daemon was killed during the audit (KOTLIN-208). Run them one at a time.
* **File descriptors.** `scripts/d4x.py` now starts every container with `--ulimit nofile=65536:65536`
  (a low default made `swift test` die with `Too many open files` on the audit host). A runner older than
  that change does not, and a host with a low Docker default then needs the limit raised by hand.
* **Options.** Several Kotlin and Elixir cases need `D4X_*` options; they are listed in
  `docs/REPLAY_KOTLIN_ELIXIR.md`. A run without them is not a failed case.
* **Online tests.** Some tests in the upstream projects reach the network (Grazie, the version lookup in
  `LatestTexifyVersionTest`, `MediaStorageTest`, `hub.docker.com` in a Phoenix test). Under
  `--network none` or behind a restricted network they can fail on the fixed side.

## What this note does not show

* It does not cover the 50 ArkTS cases: they need a device.
* It does not show that the unrelated failing tests are harmless for every use of the dataset. They are
  failures in the upstream project's own suite on the fixed revision.
* The audit and the re-check are single runs of each case.
