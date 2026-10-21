# Defects4X

**A nine-language, Defects4J-style benchmark of real-world defects with buggy/fixed revisions, production patches, trigger tests, and reproduction metadata.**

This repository is the **source-level distribution** of Defects4X. It contains:

- **850 active cases** across 9 languages
- per-case `case.json` with repository, revisions, patch references, trigger identity, and validation status
- per-case `patches/` and `environment/` metadata
- per-case oracle rows and a unified `d4x` runner
- reproduction guides for the source-reproducible languages
- container/device notes for cases that require external runtimes
- fresh KOTLIN-501 evidence (`evidence/KOTLIN-501/`)

> This is a **case-level source distribution**, not a vendored copy of every upstream repository. Full upstream source is fetched at the pinned revisions with `scripts/fetch_sources.py`; patches are applied locally. This keeps the repository reviewable and avoids redistributing third-party trees.

## Languages and cases

| Language | Cases | Reproduction path | Guide |
|---|---:|---|---|
| ArkTS | 50 | authorized device or emulator + SDK | [env/device-arkts.md](env/device-arkts.md) |
| Dart | 100 | native Dart SDK | [env/dart.md](env/dart.md) |
| Elixir | 100 | container / native OTP | [env/container.md](env/container.md) |
| Julia | 100 | native Julia | [env/julia.md](env/julia.md) |
| Kotlin | 100 | native JDK + Gradle | [env/kotlin.md](env/kotlin.md) |
| Lua | 100 | native Lua + LuaRocks | [env/lua.md](env/lua.md) |
| Perl | 100 | native Perl / container | [env/perl.md](env/perl.md) |
| R | 100 | native R 4.4.3 | [env/r.md](env/r.md) |
| Swift | 100 | container / Swift toolchain | [env/container.md](env/container.md) |

The **600 source-guide cases** are Dart, Julia, Kotlin, Lua, Perl, and R. A per-case toolchain table is in [env/case-matrix.tsv](env/case-matrix.tsv). The remaining 250 are:

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
  oracle.jsonl                # 850 per-case expected outcomes/triggers
  id-mapping.json             # Swift release ID <-> package ID
  final-case-ledger-fix9-overlay.jsonl
  release-manifest.json
  case-status-summary.json
cache/index.json              # per-case dependency-cache contract
env/                          # per-language environment guides
docs/REPRODUCTION_GUIDE.md    # generic replay protocol
docs/REPRODUCIBILITY.md       # L0-L5 status and CI scope
scripts/fetch_sources.py      # fetch upstream source at pinned revisions
scripts/d4x.py                # unified runner: list/show/fetch/patch/plan/verify
```

Each case directory is self-contained for metadata inspection. Large upstream source trees and repository bundles are intentionally not committed; they are fetched from the recorded revisions.

## Quick start

```bash
git clone https://github.com/146854hgfhbk/Defects.git
cd Defects

python scripts/d4x.py list --language dart
python scripts/d4x.py show DART-101
python scripts/d4x.py oracle DART-101

# fetch both pinned revisions
python scripts/d4x.py fetch DART-101 --out /tmp/d4x

# apply the declared trigger/production patches
python scripts/d4x.py patch DART-101 --work /tmp/d4x/DART-101 --side buggy
python scripts/d4x.py patch DART-101 --work /tmp/d4x/DART-101 --side fixed

# print the exact replay plan
python scripts/d4x.py plan DART-101

# install the toolchain from env/dart.md, then run the trigger
```

## Unified runner

`scripts/d4x.py` is a dependency-free orchestrator:

| Command | Purpose |
|---|---|
| `list` | list cases by language |
| `show` | show revisions, patches, guide, oracle |
| `oracle` | print the per-case expected outcome/trigger |
| `fetch` | clone both pinned revisions |
| `patch` | apply the selected trigger/production patches |
| `plan` | print the complete replay steps |
| `verify` | static validation of all 850 cases |

It does **not** install language toolchains or run Docker for you; it resolves the case and produces a deterministic sequence that the language guide explains.

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

See [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for L0–L5 status, [metadata/oracle.jsonl](metadata/oracle.jsonl) for per-case expectations, and [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for packaging limitations.

## License

- Code and metadata: MIT (`LICENSE`)
- Dataset metadata and documentation: CC BY 4.0 (`DATA_LICENSE`)
- Upstream source and patches remain under their original licenses; see `NOTICE`

Do not assume that a patch is relicensed by this repository. Each case records its upstream repository and issue/PR provenance.

## Citation

See `CITATION.cff`.

## Contact

Issues and reproduction reports are welcome via GitHub Issues. Please include the case ID, OS, toolchain versions, command, and the relevant `environment.lock.json`.
