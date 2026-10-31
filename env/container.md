# Container-oriented cases: Elixir and Swift

**Cases: 200**  
**Scope: exact runtime image or per-language toolchain**

## Elixir (100)

Elixir cases record a Docker backend in `case.json`:

```json
"environment": {
  "backend": "swe_rebench_v2_docker",
  "image": "local/defects4x/elixir-native-1.16.3-otp26:20261014"
}
```

Recommended:

```bash
docker run --rm -it \
  -v "$PWD:/work" -w /work \
  local/defects4x/elixir-native-1.16.3-otp26:20261014 \
  bash -lc 'MIX_ENV=test mix deps.get && MIX_ENV=test mix test <trigger>'
```

The exact image tag/digest is in the case's `environment` or `environment.lock.json`. If the image is not public, build it from the recorded Dockerfile or use the native Elixir 1.16.3 / OTP 26 toolchain and the case's `mix.lock`.

Native prerequisites:

```text
Elixir 1.16.3
Erlang/OTP 26
Hex/Rebar (offline cache for CI)
```

With `scripts/d4x.py` the compile and `mix deps.get` step needs network access and the test step
runs with `--network none`. Set `D4X_CONTAINER_NET=1` so that only the first step uses the host
network (and `https_proxy` if you need one). Each case image is 1.2 to 1.5 GB; pulls from Docker
Hub can fail midway and need several retries. ELIXIR-036 needs a network `mix deps.get` first
(about 335 MB of git dependencies). Options for cases that do not pass with the plain command are
in [docs/REPLAY_KOTLIN_ELIXIR.md](../docs/REPLAY_KOTLIN_ELIXIR.md).

## Swift (100)

Swift cases record a runtime release and image digest:

```json
"runtime_release": {
  "image_id": "sha256:...",
  "swift_executable": "/usr/bin/swift",
  "external_assets_are_required": true
}
```

Base Swift versions observed:

```text
Swift 5.10.1
Swift 6.1
Swift 6.2.3
```

The D101 addendum uses the Swift 6.2.3 image with OpenSSL. Build it from source with
[`images/build/`](../images/build/README.md):

```bash
cd images/build && make swift
docker image inspect swift-defects-validation:6.2.3-recovered-20260906-v4-openssl \
  --format '{{.Id}}'
```

The image ID differs from the one recorded in the case files; the tag is what the case
scripts and `metadata/image-tags.json` use.

Then run the case's `commands/<ID>b` and `commands/<ID>f` inside the image.

The case files do not contain the SwiftPM dependencies, so resolve them once with network before
the offline replay. The steps, the cases that need special handling, and the results are in
[docs/REPLAY_SWIFT.md](../docs/REPLAY_SWIFT.md).

## Important

- Do not treat a missing image as `PASS`; it is `BLOCKED`.
- Do not publish third-party SDK/toolchain images unless their licenses allow it.
- Pin by digest, not tag.
- Per-case bundles/caches are mounted from `cases/<lang>/<ID>/`; images should be language/runtime-level, not per-case.
