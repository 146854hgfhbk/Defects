# Dart environment guide

**Cases: 100**  
**Guide scope: native Dart SDK + pub cache**

## Versions

Dart cases use multiple SDKs. The per-case value is in `case.json` under `language_version` / `sdk_version`, and in `environment/original-dart-sdk.lock.json`.

Observed SDKs:

| SDK | Notes |
|---|---|
| 1.21.1 | legacy Dart 1 project; use the archived 1.x SDK |
| 2.0.0, 2.5.2, 2.7.2, 2.9.3 | old null-safety transition projects |
| 2.10.5, 2.12.4, 2.13.4, 2.14.4 | late 2.x |
| 2.18.6, 2.19.6 | most common 2.x |
| 3.5.4, 3.10.0, 3.12.2 | Dart 3 projects |

Do **not** install one global Dart and run all cases. Read the lock first:

```bash
python - <<'PY'
import json
c=json.load(open('cases/dart/DART-101/case.json'))
print(c.get('language_version'))
print(c.get('sdk_version'))
print(c.get('environment'))
PY
```

## Install

Download the exact SDK from the Dart archive:

```bash
export DART_VERSION=3.10.0
mkdir -p "$HOME/d4x/dart-$DART_VERSION"
curl -fL -o /tmp/dart.zip \
  "https://storage.googleapis.com/dart-archive/channels/stable/release/${DART_VERSION}/sdk/dartsdk-linux-x64-release.zip"
unzip -q /tmp/dart.zip -d "$HOME/d4x/dart-$DART_VERSION"
export PATH="$HOME/d4x/dart-$DART_VERSION/dart-sdk/bin:$PATH"
dart --version
```

For versions no longer in the `stable` channel, use the archive bucket or a mirrored SDK tarball. Keep the SHA256 in `environment/original-dart-sdk.lock.json`.

## Dependencies

```bash
export PUB_CACHE="$HOME/d4x/pub-cache-$DART_VERSION"
dart pub get --offline   # if the case ships a dependency cache
# or, when online preparation is allowed:
dart pub get
```

Dart cases often pin `pubspec.lock`. Do not run `dart pub upgrade`.

## Build and trigger

```bash
dart analyze
dart test --reporter=json <declared test file or name>
```

Use the command declared in `case.json` (`build.test_command`), not a blanket `dart test` of the whole repo.

## Network isolation

Many Dart cases are validated with an OS-enforced network namespace. Prepare `PUB_CACHE` first, then:

```bash
unshare -n -- bash -lc 'dart test --reporter=json test/...'
```

## Common failures

- `The current Dart SDK version is ...` — wrong SDK; switch to the case lock.
- `Because ... requires SDK version ...` — old `pubspec.yaml` constraint; do not edit it unless the case says `build_compatibility`.
- Missing `pubspec.lock` / package cache — use the case's `environment/dependency-cache-manifest.json`.
- Tests hang on `dart pub get` — network is disabled; pre-populate `PUB_CACHE`.
