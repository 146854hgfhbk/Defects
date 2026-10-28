# KOTLIN-501 replay (clean server)

One run of `scripts/d4x.py run KOTLIN-501` on 2026-10-28.

- buggy: `FAIL_AS_EXPECTED` (31 tests, 1 failed: the trigger test)
- fixed: `PASS`
- repetitions: 1 (not a strict multi-repetition replay)

Environment: JDK 17, Gradle 8.3 (wrapper), Node 20.20.2, Chrome for Testing 148 launched with
`--no-sandbox` through a wrapper script (the host disables unprivileged user namespaces).
Puppeteer 24.43.1 is installed by the test itself with `npm`. The Node and Chrome versions are
not the ones listed in `case.json` (Chrome 151).

Files: `result.json`, the four Gradle logs, `SHA256SUMS`.
