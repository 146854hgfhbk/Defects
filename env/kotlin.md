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

Install Node only. Do **not** pre-install Puppeteer: `NodeNpmWrapperTest` asserts that it is not
linked, so a pre-installed copy fails the test on both sides. The test installs Puppeteer itself
through `npm` (set `npm_config_registry=https://registry.npmjs.org` if your npm default is a mirror).
The replay host launched Chrome for Testing 148 rather than 151; on Ubuntu 24.04 AppArmor blocks
unprivileged user namespaces, so Chrome needs a `--no-sandbox` wrapper (point
`PUPPETEER_EXECUTABLE_PATH` at it).

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
- Wrapper tries to download Gradle — pre-populate `GRADLE_USER_HOME/wrapper/dists`.
- Android SDK required — check `build.android_sdk_required` and install the matching SDK.
- KOTLIN-501 PDF test hangs — Chrome/Puppeteer missing or wrong version.
- `.\gradlew.bat: not found`: 88 cases record the Windows launcher in `build_command` /
  `test_command`. On Linux run `./gradlew` with the same arguments; `d4x` does this itself.
- Fixed side fails to compile with `Unresolved reference`, or a case needs an option such as a longer
  timeout: see [docs/REPLAY_KOTLIN_ELIXIR.md](../docs/REPLAY_KOTLIN_ELIXIR.md), which lists the
  `D4X_KOTLIN_*` options and the cases that need them.
