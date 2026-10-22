# Clean-room image builds

> **Security notice:** the reference server that produced the original
> `docker save` tars was compromised. Those tars are **not trusted**. This
> directory rebuilds the runtime images from official base images.

## What is here

```text
images/build/
  Makefile
  swift/Dockerfile
  elixir/Dockerfile
  versions.lock
```

There are **no binaries**, no caches, and no toolchain tarballs from the
reference server.

## Build

Requirements:

- Linux x86_64
- Docker with Buildx
- network access to Docker Hub and the distribution package repository

```bash
cd images/build
make build
```

Or one language:

```bash
make swift
make elixir
```

Every build uses:

```text
--pull --no-cache --load
```

and installs dependencies from the base image's official package repository.

For provenance/attestations, push to a registry instead of `--load`:

```bash
docker buildx build --push --provenance=true --sbom=true ...
```

## Tags

The Makefile produces the tags expected by the dataset:

```text
swift-defects-validation:5.10.1-restored-20260908
swift-defects-validation:6.1-recovered-20260905
swift-defects-validation:6.2.3-recovered-20260906-v2
swift-defects-validation:6.2.3-recovered-20260906-v3-sqlite
swift-defects-validation:6.2.3-recovered-20260906-v4-openssl
local/defects4x/elixir-native-1.16.3-otp26:20261014
local/defects4x/elixir-msz-hammox-python:20260929
```

## Verify

```bash
make verify
```

This runs `swift --version` / `elixir --version` inside each image.

## Scan

```bash
make scan
```

Uses Trivy if installed. The build does not claim the images are CVE-free.

## Important: image IDs will differ

The original image IDs (for example the D101 `sha256:da8756...` ID) were built
from the compromised server's local base images and toolchain tarballs.
A clean rebuild **will not be byte-identical**.

That is expected. The reproduction contract is:

- same Swift/Elixir major/minor runtime
- same system dependencies
- same case source and patches
- same trigger outcome

not the same image digest.

If you need a byte-identical image, you must first rebuild the exact original
base/toolchain from trusted sources and pin every layer by digest.

## Pinning base images

`versions.lock` lists the base tags. For a release, resolve and pin the digest:

```bash
docker buildx imagetools inspect swift:6.2.3-jammy
docker buildx imagetools inspect elixir:1.16.3-otp-26
```

then change the base to:

```dockerfile
FROM swift:6.2.3-jammy@sha256:...
```

Do not use `latest`.

## Do not

- `docker load` old tars from the reference server
- copy `.gradle`, Julia depot, CPAN, LuaRocks, or R libraries from the server
- use `ADD`/`COPY` from `/data/users/...`
- build with a warm cache and call it clean
