# Kotlin environment guide

**Cases: 100**  
**Guide scope: native JDK + Gradle wrapper**

## Versions

Kotlin cases are heterogeneous:

| Component | Observed values |
|---|---|
| JDK | 8 (1 case), 11 (2), 17 (49), 21 (42), 25 (6) |
| Gradle | 35 distinct `build.gradle_version` values, from 7.2 to 9.5.1; the wrapper in each checkout downloads its own |
| Kotlin | 2.1.0, 2.2.21, 2.3.10, 2.3.20, 2.3.21, 2.4.0 |

Read the case:

```bash
python - <<'PY'
import json
c=json.load(open('cases/kotlin/KOTLIN-001/case.json'))
print(json.dumps(c['build'], indent=2))
print(json.dumps(c.get('dependency_versions'), indent=2))
PY
```

`case.json.build.java_version` and `build.gradle_version` are authoritative.

## Install JDK

Use a JDK distribution matching the case (Temurin is a good default):

```bash
export JDK_VERSION=17
curl -fL -o /tmp/jdk.tar.gz \
  "https://github.com/adoptium/temurin${JDK_VERSION}-binaries/releases/download/jdk-${JDK_VERSION}.0.20%2B10/OpenJDK${JDK_VERSION}U-jdk_x64_linux_hotspot_${JDK_VERSION}.0.20_10.tar.gz"
mkdir -p "$HOME/d4x/jdk-$JDK_VERSION"
tar -xzf /tmp/jdk.tar.gz -C "$HOME/d4x/jdk-$JDK_VERSION" --strip-components=1
export JAVA_HOME="$HOME/d4x/jdk-$JDK_VERSION"
export PATH="$JAVA_HOME/bin:$PATH"
java -version
```

For JDK 8, 11, 21 and 25 use the corresponding Temurin release (the replay host used the
distribution's OpenJDK packages). If the case pins `java_vendor`, match it.

`d4x` does not choose the JDK: install all five and set `JAVA_HOME` and `PATH` from
`build.java_version` before each `d4x run`. Do not set `JAVA_TOOL_OPTIONS`: every JVM then prints
`Picked up JAVA_TOOL_OPTIONS` to stderr, and tests that assert an empty stderr fail on both sides
(KOTLIN-107). Put the proxy in `gradle.properties` (`systemProp.https.proxyHost`, ...) instead.

## Gradle

Prefer the repository's Gradle wrapper:

```bash
export GRADLE_USER_HOME="$HOME/d4x/gradle-home"
./gradlew --version
```

If the wrapper distribution is not available offline, download the exact distribution declared in `gradle/wrapper/gradle-wrapper.properties` and set `GRADLE_USER_HOME`.

Do not upgrade Gradle. Old projects often fail on newer Gradle/JDK combinations.


### KOTLIN-100: prepare the wrapper before replay

KOTLIN-100 uses `projects/gradle/wrapper/gradle-wrapper.properties`, Gradle
**8.14.3-bin** and JDK 17. Its wrapper URL redirects to GitHub release assets;
on a host where that download stalls, the failure occurs before compilation or
any test. A timed-out wrapper can keep the default `~/.gradle` lock until its
child process exits, blocking a later side as well. Treat that as `BLOCKED`, not
a bug failure. Check the process and the lock owner before retrying; do not delete
a lock file while another process holds it.

Choose the JDK and a Gradle home explicitly. For a fresh cache, pre-stage the
exact distribution with the included helper. It accepts the official URL by
default or a local archive / reachable mirror as the first argument. The helper
verifies the pinned SHA-256 from Gradle's official checksum, preserves the
wrapper URL's cache key, and refuses to overwrite an existing or partial entry.
It needs `bash`, `python3`, `sha256sum` and `curl` (for a URL).

```bash
export JAVA_HOME="$HOME/d4x/jdk-17"
export PATH="$JAVA_HOME/bin:$PATH"
export GRADLE_USER_HOME="$HOME/d4x/kotlin100-gradle-home"

# Default source: https://services.gradle.org/distributions/gradle-8.14.3-bin.zip
scripts/prepare_kotlin100_gradle.sh
# If the official download route stalls, use a reachable mirror or a local ZIP:
# scripts/prepare_kotlin100_gradle.sh https://mirrors.cloud.tencent.com/gradle/gradle-8.14.3-bin.zip
# scripts/prepare_kotlin100_gradle.sh /path/to/gradle-8.14.3-bin.zip

python3 scripts/d4x.py run KOTLIN-100 --work "$HOME/d4x/kotlin100-replay" \
  --side both --mode local --timeout 1800
```

The helper pins `bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531`;
the official checksum can be checked independently at
`https://services.gradle.org/distributions/gradle-8.14.3-bin.zip.sha256`.
The helper creates `caches/8.14.3` so Gradle's distribution cleanup sees a
matching version. It prepares only Gradle itself: project plugins and dependencies
must also be available from the configured repositories or a prepared dependency
cache. Set proxy properties only when the proxy is running and needed; do not copy
another host's proxy endpoint blindly. See the cache-cleanup details in
[the second-host audit](../docs/REPLAY_SECOND_HOST_AUDIT.md).

**Verified on 2026-11-11:** with an existing prepared Gradle home and its
previously populated dependency cache, Temurin 17.0.21, Gradle 8.14.3 and the
command above, the buggy side compiled (39 s) and its trigger failed as expected
(1 failure in 294 tests, 2 skipped); the fixed side compiled and the full declared
`jvmTest` task exited 0. `result.json` reported `PASS`. JUnit XML identifies the
buggy trigger as `java.lang.ClassCastException` at `PropertyRegistryExt.kt:59`;
the fixed trigger XML has zero failures. This was one replay using a warm cache,
not an offline clean-install or stability claim. The case records Temurin 17.0.19;
17.0.21 is the observed host version for this run.


## KOTLIN-501 sidecar

One case additionally needs a browser/PDF stack:

| Component | Version |
|---|---|
| Node.js | 20.20.2 |
| npm | 10.8.2 |
| Puppeteer | 24.43.1 |
| Chrome for Testing | 151.0.7922.47 |

```bash
export NODE_HOME="$HOME/d4x/node-v20.20.2"
export PATH="$NODE_HOME/bin:$PATH"
node --version
npm --version
```

The exact profile is in `cases/kotlin/KOTLIN-501/case.json` under `runtime_prerequisites`.

Two setups were run on the second host: the sidecar the case declares (Node 20.20.2 with Puppeteer
24.43.1 installed globally, Chrome for Testing 151) and the same Node with the global Puppeteer
removed. With both, the buggy side fails the trigger as expected and `NodeNpmWrapperTest` passes. An earlier
version of this note said that a pre-installed Puppeteer makes `NodeNpmWrapperTest` fail; that was seen
on the clean host and was not reproduced on the second host, so it is not a rule. Set
`npm_config_registry=https://registry.npmjs.org` if your npm default is a mirror.

Chrome must be able to start, or the four PDF tests in `CompileCommandTest` fail on **both** sides and the
trigger cannot tell them apart (seen with a missing Chrome path and with a Chrome that had no shared
libraries). Two things stop it on a stock host:

* Ubuntu 24.04 restricts unprivileged user namespaces, so Chrome needs `--no-sandbox`. Point
  `PUPPETEER_EXECUTABLE_PATH` at a wrapper script that adds it.
* Missing shared libraries (`libasound.so.2` on the second host). Add the directory that holds them to
  `LD_LIBRARY_PATH` in the same wrapper.

Check it before the run: `chrome-wrapper --headless=new --disable-gpu --print-to-pdf=/tmp/x.pdf "data:text/html,<h1>ok</h1>"`
must write a PDF.

Even with a working Chrome the fixed side fails `MediaStorageTest > media storage()` on a host that cannot
reach `raw.githubusercontent.com`: the test downloads images from it and ends with
`java.net.SocketException: Connection reset`.

## Android cases

KOTLIN-001 and KOTLIN-120 to 123 have `build.android_sdk_required`. Install Android SDK platform 34
and build-tools 34.0.0 into `$HOME/d4x/android-sdk`; `d4x` sets `ANDROID_HOME` from that directory
when it exists. These modules have no `testClasses` task, so `d4x` runs the case's own
`compile_task` / `test_task`.

## Build and test

```bash
./gradlew :module:testClasses --no-daemon --offline
./gradlew :module:test --tests 'fully.qualified.Test' --no-daemon --offline
```

Use the case's `build.compile_task` / `build.test_task`; do not run the whole multi-module build.

## Common failures

- `Unsupported class file major version` — JDK too new/old.
- `Could not resolve ...` — Gradle cache missing; prepare online, then `--offline`.
- Wrapper tries to download Gradle (`Downloading https://services.gradle.org/...` then `Connect timed out`).
  The download is redirected through `github.com` to `release-assets.githubusercontent.com`, so the host
  must reach those too; check with `curl -sSIL <distributionUrl>`, not with the `.sha256` file or the
  directory page, which `services.gradle.org` answers itself. Alternatively pre-populate
  `GRADLE_USER_HOME/wrapper/dists`, and then stop Gradle from cleaning it up: Gradle deletes a
  distribution that has no `caches/<version>/` directory. Put the init script from
  [docs/REPLAY_SECOND_HOST_AUDIT.md](../docs/REPLAY_SECOND_HOST_AUDIT.md) in `GRADLE_USER_HOME/init.d`
  (it cannot be set in `gradle.properties`) and create an empty `caches/<version>/` for each kept
  distribution. 24 Kotlin cases ended BLOCKED on the second host for this reason.
- Build fails with `Error while reading dataframe from data at https://raw.githubusercontent.com/...`
  (KOTLIN-160, 161, 162): the build reads a file from `raw.githubusercontent.com`; the host must reach it.
- Android SDK required — check `build.android_sdk_required` and install the matching SDK.
- KOTLIN-501 PDF test hangs — Chrome/Puppeteer missing or wrong version.
- `.\gradlew.bat: not found`: 88 cases record the Windows launcher in `build_command` /
  `test_command`. On Linux run `./gradlew` with the same arguments; `d4x` does this itself.
- Fixed side fails to compile with `Unresolved reference`, or a case needs an option such as a longer
  timeout: see [docs/REPLAY_KOTLIN_ELIXIR.md](../docs/REPLAY_KOTLIN_ELIXIR.md), which lists the
  `D4X_KOTLIN_*` options and the cases that need them.
