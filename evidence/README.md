# Evidence

## KOTLIN-501

`evidence/KOTLIN-501/` is a fresh 2026-10-21 replay with the Kotlin `1.0.5-hfprep-20261015` package.

- repetitions: 3
- strict: true
- full suite: true
- result: PASS
- buggy: `FAIL_AS_EXPECTED` (3/3)
- fixed: `PASS` (3/3)

Files:

- `context.json` — framework version, revisions, trigger identity, toolchain requirements
- `summary.json` — per-repetition compile/full-suite/trigger results
- `runs/` — command records, logs, JUnit XML
- `EVIDENCE_MANIFEST.json` — SHA256 bindings for every evidence file

The evidence was produced on a clean work root with JDK 17.0.20.1, Gradle 8.3, Node 20.20.2, npm 10.8.2, Puppeteer 24.43.1, and Chrome for Testing 151.0.7922.47. Host paths were sanitized to `__REFERENCE_*__` before publication.

Other cases currently have `oracle_level: DECLARED`; their evidence remains in the original release packages or is pending an independent clean-room replay.
