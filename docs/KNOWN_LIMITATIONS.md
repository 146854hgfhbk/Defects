# Known limitations

This repository is a **snapshot** of the 850-case release metadata and per-case source-level records. It is not a claim that all 850 cases are fully reproducible from this repository alone.

## Reproduction tiers

- 600 cases have a per-language source guide: Dart, Julia, Kotlin, Lua, Perl, R.
- 200 cases are container-oriented: Elixir and Swift.
- 50 ArkTS cases are device-oriented.

## Packaging issues carried over from the source release

1. **KOTLIN-501 evidence provenance (resolved)**
   The source-release bundle was produced with Kotlin `1.0.2-blockerfix`. It has been re-run with `1.0.5-hfprep-20261015` on 2026-10-21: 3/3 strict repetitions PASS (buggy FAIL_AS_EXPECTED, fixed PASS). New evidence is in `evidence/KOTLIN-501/`; `metadata/oracle.jsonl` marks it `EVIDENCED`.

2. **Older package versions in the release manifest**
   The manifest still points at Elixir `1.1.1`, R `1.0.1/r-106`, and Swift `1.1.1/99` base. Newer packages exist (Elixir 1.1.3, R-100 1.1.0, Swift 1.1.2). The per-case `case.json` records what the case needs; the manifest may lag.

3. **Absolute host paths**
   Historical `/data/users/...` paths were sanitized to `__REFERENCE_USER_HOME__` / `__REFERENCE_USER__`. They are provenance placeholders, not runnable paths. Use `repository_url` + revision, or the case's bundle/cache.

4. **Swift ID aliases**
   Active IDs are `SWIFT-Dxxx`; package-internal `case_id` values are older `SWIFT-xxx` / `CASES-SWIFT-xxx`. `metadata/id-mapping.json` is the canonical mapping; use `release_case_id` for paths/oracle and `package_case_id` only when a package script requires it.

5. **R cap and Dart extras**
   The R package contains 106 source records; the active release keeps 100. Dart packages may contain 6 non-active extras. Always filter with `metadata/cases.jsonl`.

6. **Perl audit status**
   Some Perl cases carry `audit.license_evidence: BLOCKED` or `status.audit` warnings. Check the case before redistribution or publication claims.

7. **Dependency caches are recipes, not artifacts**
   `cache/index.json` records the lock path for each case, but large cache tarballs are not committed. Materialize them from the language guide; set `artifact`/`status: available` only after uploading a verified archive.

8. **Unified runner scope**
   `scripts/d4x.py` orchestrates fetch/patch/plan/static verification. It does not install toolchains, pull 500GB of images, or provide an ArkTS device/emulator.

## What this repository does not contain

- full upstream repositories
- large repository bundles / dependency caches
- proprietary SDKs or device signing material
- prebuilt Docker images

Those are external assets, referenced by per-case `environment` / `runtime_release` fields.
