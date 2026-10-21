# Reproducibility status

Defects4X distinguishes five levels. A claim should name the level.

| Level | Meaning | Current status |
|---|---|---|
| L0 | metadata, patches, locks are readable | 850/850 |
| L1 | upstream source can be fetched at pinned revisions | 850/850 by script design; Lua fixed and smoke-tested |
| L2 | correct toolchain can be installed from a guide | 600 language guides + 250 container/device notes |
| L3 | buggy FAIL / fixed PASS replay | partially evidenced; not independently re-run for 850 |
| L4 | clean-room, offline, evidence-hash match | not yet |
| L5 | third party succeeds first try | not yet |

## What CI checks

`.github/workflows/static.yml` checks:

- 850 case records parse
- every case has an oracle entry
- every Swift case has an ID mapping
- no tracked file exceeds 100 MB
- each language has a plan for a smoke case

It does **not** run the language toolchains, Docker images, or ArkTS devices. Those are L3/L4 and require self-hosted runners.

## Known gaps

- Binary images are referenced by digest, not stored in GitHub.
- Swift reference images and ArkTS devices are external prerequisites.
- KOTLIN-501 evidence is marked `STALE` until re-run with Kotlin 1.0.5.
- 299 case manifests still point at older package versions.
- 220 historical host paths are placeholders (`__REFERENCE_*__`).

## Clean-room checklist

For each case:

1. `python scripts/d4x.py fetch <CASE> --out /tmp/d4x`
2. `python scripts/d4x.py patch <CASE> --work /tmp/d4x/<CASE> --side buggy`
3. `python scripts/d4x.py patch <CASE> --work /tmp/d4x/<CASE> --side fixed`
4. install the toolchain from `env/<language>.md`
5. run the oracle command with network disabled
6. record exit codes, JUnit/XML, toolchain versions
7. compare with `metadata/oracle.jsonl`

A case is `L4` only when the log and patch hashes are recorded and reproducible on a second clean machine.
