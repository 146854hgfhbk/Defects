# Security notice

**2026-10-22: the reference server used to build the original images was
compromised by a worm.**

## What is affected

- The original `docker save` tars under `images/binaries/` were produced on the
  compromised server.
- Caches on that server (`.gradle`, Julia depot, CPAN/LuaRocks/R libraries,
  browser caches) are untrusted.
- The reference toolchain tarballs and local base images are untrusted.

## What is not trusted

Do **not**:

- `docker load` any old Defects4X image tar
- run images built from the old server's local base images
- copy caches or toolchain tarballs from `/data/users/...`
- reuse credentials that were present on that server

The 7 old image tars have been removed from the Hugging Face dataset and
replaced with clean-room build recipes.

## What to use

Build from source:

```bash
cd images/build
make build
make verify
```

This starts from official base images, installs dependencies from the
distribution's package repository, and does not consume any server cache.

See:

- `images/build/README.md`
- `images/build/Makefile`
- `images/build/swift/Dockerfile`
- `images/build/elixir/Dockerfile`

## Credentials

Rotate anything that was present on the server or shared in logs/chat:

- GitHub personal access tokens and SSH keys
- Hugging Face tokens
- Docker Hub / GHCR credentials
- cloud provider credentials
- any tokens in Docker images, caches, shell history, cron, or systemd units

## Reporting

If you find a suspicious file, layer, or behavior in an image, open a GitHub
issue with the image tag, digest, `docker history`, and the command used.
