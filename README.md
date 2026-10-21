# Defects4X

**A nine-language, Defects4J-style benchmark of real-world defects with buggy/fixed revisions, production patches, trigger tests, and reproduction metadata.**

This repository is the **source-level distribution** of Defects4X. It contains:

- **850 active cases** across 9 languages
- per-case `case.json` with repository, revisions, patch references, trigger identity, and validation status
- per-case `patches/` and `environment/` metadata
- reproduction guides for the source-reproducible languages
- container/device notes for cases that require external runtimes

> This is a **case-level source distribution**, not a vendored copy of every upstream repository. Full upstream source is fetched at the pinned revisions with `scripts/fetch_sources.py`; patches are applied locally. This keeps the repository reviewable and avoids redistributing third-party trees.

## Languages and cases

| Language | Cases | Reproduction path | Guide |
|---|---:|---|---|
| ArkTS | 50 | authorized device + SDK | [env/device-arkts.md](env/device-arkts.md) |
| Dart | 100 | native Dart SDK | [env/dart.md](env/dart.md) |
| Elixir | 100 | container / native OTP | [env/container.md](env/container.md) |
| Julia | 100 | native Julia | [env/julia.md](env/julia.md) |
| Kotlin | 100 | native JDK + Gradle | [env/kotlin.md](env/kotlin.md) |
| Lua | 100 | native Lua + LuaRocks | [env/lua.md](env/lua.md) |
| Perl | 100 | native Perl / container | [env/perl.md](env/perl.md) |
| R | 100 | native R 4.4.3 | [env/r.md](env/r.md) |
| Swift | 100 | container / Swift toolchain | [env/container.md](env/container.md) |

The **600 source-guide cases** are Dart, Julia, Kotlin, Lua, Perl, and R. The remaining 250 are:

- **200 container-oriented cases**: Elixir 100 + Swift 100
- **50 device-oriented cases**: ArkTS 50

Reproduction guides do not by themselves imply that a case passed; always check the case's `status`, `validation`, and `environment` fields.

## Repository layout

```text
cases/
  <language>/<CASE_ID>/
    case.json                 # repository, revisions, trigger, patch refs, status
    patches/                  # minimized/source/test/trigger patches where available
    environment.lock.json     # toolchain/container lock (when supplied by the package)
    environment/              # per-case dependency locks, Dockerfile, manifests
    trigger/                  # trigger scripts (Julia/Lua etc.)
    commands/                 # runner commands (Swift etc.)
metadata/
  cases.jsonl                 # 850-case canonical ledger
  final-case-ledger-fix9-overlay.jsonl
  release-manifest.json
  case-status-summary.json
env/                          # per-language environment guides
docs/REPRODUCTION_GUIDE.md    # generic replay protocol
scripts/fetch_sources.py      # fetch upstream source at pinned revisions
```

Each case directory is self-contained for metadata inspection. Large upstream source trees and repository bundles are intentionally not committed; they are fetched from the recorded revisions.

## Quick start

```bash
git clone https://github.com/146854hgfhbk/Defects.git
cd Defects

# 1. choose a case
python - <<'PY'
import json
for line in open('metadata/cases.jsonl'):
    c=json.loads(line)
    if c['case_id']=='DART-101':
        print(json.dumps(c,indent=2))
PY

# 2. fetch its upstream repository at the pinned revisions
python scripts/fetch_sources.py DART-101 --out /tmp/d4x-src

# 3. install the toolchain from the language guide, then replay
#    see env/dart.md and docs/REPRODUCTION_GUIDE.md
```

## Patch semantics

For most cases:

- `buggy` = buggy revision + trigger/test patch
- `fixed` = buggy revision + production patch + trigger/test patch

Always use the patch roles declared in `case.json` (`original_patch`, `minimized_patch`, `source_fix`, `trigger`, etc.). Do not apply the whole upstream commit blindly.

## Reproducibility status

The benchmark distinguishes:

- `SOURCE_REPRODUCIBLE` — source + pinned toolchain guide
- `CONTAINER_REQUIRED` — exact runtime image or image digest is needed
- `DEVICE_REQUIRED` — authorized device/SDK/signing material is needed
- `BLOCKED` / `PARTIAL` — recorded in the case metadata

See `metadata/case-status-summary.json` for aggregate counts and each `case.json` for the per-case status. Known packaging limitations are documented in [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md).

## License

- Code and metadata: MIT (`LICENSE`)
- Dataset metadata and documentation: CC BY 4.0 (`DATA_LICENSE`)
- Upstream source and patches remain under their original licenses; see `NOTICE`

Do not assume that a patch is relicensed by this repository. Each case records its upstream repository and issue/PR provenance.

## Citation

See `CITATION.cff`.

## Contact

Issues and reproduction reports are welcome via GitHub Issues. Please include the case ID, OS, toolchain versions, command, and the relevant `environment.lock.json`.
