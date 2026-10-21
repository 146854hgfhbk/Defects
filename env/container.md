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

The D101 addendum requires the exact image:

```text
swift-defects-validation:6.2.3-recovered-20260906-v4-openssl
sha256:da8756f80cc1f5df7a777e662785a70fc990d06bd51d8fa02929366c30d98778
size: 3122238068 bytes
```

This image is an external asset. Verify its SHA256, then:

```bash
docker load --input swift-defects-validation-6.2.3-recovered-20260906-v4-openssl.tar.gz
docker image inspect swift-defects-validation:6.2.3-recovered-20260906-v4-openssl \
  --format '{{.Id}}'
```

Then run the case's `commands/<ID>b` and `commands/<ID>f` inside the image.

## Important

- Do not treat a missing image as `PASS`; it is `BLOCKED`.
- Do not publish third-party SDK/toolchain images unless their licenses allow it.
- Pin by digest, not tag.
- Per-case bundles/caches are mounted from `cases/<lang>/<ID>/`; images should be language/runtime-level, not per-case.
