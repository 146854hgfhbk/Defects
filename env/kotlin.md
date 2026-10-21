# Kotlin environment guide

**Cases: 100**  
**Guide scope: native JDK + Gradle wrapper**

## Versions

Kotlin cases are heterogeneous:

| Component | Observed values |
|---|---|
| JDK | 17, 21, 25 |
| Gradle | 7.2, 7.4.2, 7.5.1, 7.6, 8.2.1, 8.3, 8.4, 8.5, 8.6, 8.8, 8.10, 8.10.2, 8.14.3, 9.2.0, 9.2.1, 9.4.0, 9.5.1 |
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

For JDK 21/25 use the corresponding Temurin release. If the case pins `java_vendor`, match it.

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
