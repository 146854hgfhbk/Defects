# Replay notes: Dart, Perl, Julia, Lua, R

Replay of the Dart, Perl, Julia, Lua and R cases (100 each) on a clean Ubuntu 24.04
host (2 vCPU, 7 GB RAM), run with `scripts/d4x.py`. Written 2026-10-26.

## Result

| Language | Cases | Latest run of each case | How the verdict is taken |
|---|---|---|---|
| Dart | 100 | 100 PASS (8 run directories) | by trigger test name |
| Perl | 100 | 100 PASS (see Perl) | exit code of the trigger command |
| Julia | 100 | 100 PASS (6 run directories) | trigger script / test command exit code |
| Lua | 100 | 100 PASS (one run, reference mode) | `busted` selector exit code |
| R | 100 | 100 PASS (2 run directories) | by trigger test name |

PASS means: buggy side `FAIL_AS_EXPECTED` and fixed side `PASS`.

**What this does not show.** The 500 results come from several runs made while `d4x`
was being fixed, so they were not all produced by the final code and the final option
set. One single re-run of all 500 with the final `scripts/d4x.py` has not been done.
Only PERL-004 and PERL-059 were re-run with the final code and options (both PASS).

**These are not the dataset exactly as shipped.** Each language needs the `d4x` options
below, extra toolchain pieces, or a different way to judge the result. Treat a PASS as
"reproduces under these options", and report the options with it.

## Common setup

```bash
git clone https://github.com/146854hgfhbk/Defects.git && cd Defects
python3 scripts/d4x.py run <CASE_ID> --work /tmp/d4x-work/<CASE_ID> --force
```

Long runs exceed typical SSH command limits: use `nohup` and poll. If the host cannot
reach GitHub, CRAN, Julia or Dart mirrors directly, set `https_proxy` / `http_proxy`.
`D4X_CLONE_RETRIES` controls clone retries (default 5).

## Dart

* Pick the SDK per case from `environment/Dockerfile.reproduction`
  (`release/<version>/sdk`); fall back to 2.19.6. One `PUB_CACHE` per SDK version.
* The verdict is taken from the named trigger tests (matched by suite path), not from
  the exit code of the whole suite.
* Options used for specific cases (set in the environment; the per-case choice was not
  recorded in a single script):
  * `D4X_STAGE_DART_LOCK=1`: pin the case's `post-minimization-*-pubspec.lock`.
  * `D4X_DART_UNSOUND=1`: `dart --no-sound-null-safety`. Only for cases whose SDK is
    below 3; do not use it for DART-662 (SDK 3.5.4).
  * `D4X_DART_ANALYZE_ADVISORY=1`: do not stop on `dart analyze` (DART-557: the
    reference run also exits 3 there).
  * `D4X_DART_TRIGGER_FILES=1`: run only the trigger test files (DART-1148 has
    unrelated tests that hang for 12 minutes).
* `dart analyze` runs per directory (the old call failed with "Only one directory is
  expected"). On the fixed side a trigger patch whose added lines are already in the
  file counts as applied (DART-1120).
* `iverilog` is needed by 7 cases. SDK 2.0.0-dev.69.5 (dev channel) is needed by the
  oldest cases.

## Perl

* The system Perl is 5.38 (threaded); the cases record 5.36. PERL-243 and PERL-307 only
  pass with a non-threaded 5.36.3 built from source (XS code using `aTHX_`).
* Final option set:

  ```bash
  export LANG=C LC_ALL=C
  export PERL5LIB=lib:$HOME/d4x/perl5b/lib/perl5
  export D4X_PERL_DERIVE_CMD=1     # 33 cases ship commands.trigger_test = null
  export D4X_PERL_DERIVE_BUILD=1   # build XS / in-tree so the checkout, not an installed copy, is tested
  export D4X_PERL_MAKE_ARGS='DEFINE="-Wno-error=declaration-after-statement"'
  ```

  `D4X_PERL_DERIVE_CMD` builds `prove -Ilib -It/lib <trigger.test_file>` from the case's
  `trigger.test_file`. That command is derived by `d4x`, not declared by the dataset.
* Extra CPAN modules were installed under `~/d4x/perl5b`: Test::Needs, Exception::Class,
  Term::Table, Test::Warn, IO::Compress::Brotli/Zstd, Clone and others. PERL-097
  (Dist::Zilla, no `Makefile.PL`) needs `lib` first in `PERL5LIB`. PERL-059 needs
  `LANG=C`. The Cpanel-JSON-XS cases (150, 174, 186, 190, 197) need the `DEFINE` above.
* Re-checked on 2026-10-26 with the final code and options: PERL-004 PASS, PERL-059 PASS.
  Earlier summaries show them as FAIL because those runs lacked a module (004) or the
  locale (059).

## Julia

* Julia version per case from `language_version`: 1.6.7, 1.8.5, 1.9.1, 1.12.7, default
  1.10.12. Install them under `$D4X_HOME/julia-<version>` (default `~/d4x`).
* 47 cases have `revision_mode = fixed_minus_minimized_patch`: the buggy tree is the fixed
  revision with the minimized patch reverse-applied. `d4x` does that (`_reverse_buggy`);
  without it buggy equals fixed.
* Trigger script comes from `case.json` `trigger.path` (JULIA-055 does not use
  `trigger.jl`). When `trigger.mode` is `dedicated_script`, the stale
  `upstream-tests.patch` is skipped (JULIA-384, JULIA-706).
* `D4X_JULIA_PRECOMPILE=1` for JULIA-490: its trigger runs a child under `timeout 60s`
  and on a 2-core host the first `using` otherwise spends that budget precompiling.
* The case's own per-side `Project.toml` / `Manifest.toml` are staged into the worktree.

## Lua

* **Reference mode** (the mode behind the 100 PASS): `D4X_LUA_REFERENCE=1 LUA54=1`.
  It copies the dataset's own `scripts/run_targeted_case.ps1` logic: no patch is applied;
  the fixed side is the fixed commit as is; the buggy side is the buggy commit plus the
  regression test file copied from the fixed commit. Earlier patch-simulation runs gave
  73 PASS; 27 cases failed there for reasons listed below, so the two modes are not
  interchangeable.
* Toolchain: Lua 5.4 under `~/d4x/lua54` (`LUA54=1` puts it first in `PATH`), plus
  busted 2.3, luacov and luafilesystem. The default `lua` on `PATH` stays 5.1.
* Seven files are not in the earlier tree and were restored:
  `cases/lua/EV-LU-{156,172,173,174,175,176,177}/evidence/d4j_trigger.lua`. They came from
  the `dataset/golden/<id>/evidence/` directory of the Lua package produced on the
  reference server that was later found compromised. Their sha256 equals the one in each
  case's `SHA256SUMS`, and that is the only reason to trust them. Re-derive or re-review
  before relying on them.
* Not seen in patch mode but needed there: `luacov` (11 cases), and for EV-LU-091
  `LUA_PATH="./src/?.lua;./src/?/init.lua;;"` so the repository's own `argparse` is
  loaded.

## R

* R 4.4.3 from Posit (Ubuntu 24.04 ships 4.3.3):

  ```bash
  export PATH=/opt/R/4.4.3/bin:$PATH R_LIBS=$HOME/d4x/Rlib
  export D4X_R_CASE_LIB=1                         # install the package under test into a per-case library
  export D4X_R_TRIGGERS=$PWD/metadata/r-trigger-tests
  ```

  `D4X_R_CASE_LIB=1` matters: installing every checkout into the shared library
  overwrote 24 packages and left 34 cases BLOCKED.
* Verdict by trigger test name. `metadata/r-trigger-tests/<CASE>.txt` lists one
  `file :: [context / ]test` per line, 140 names for the 100 cases. `d4x` runs
  `scripts/r_trigger_report.R` (with `NOT_CRAN=true`) and judges on those names.
  The fixed side can still have unrelated failing tests (`other_failures` in
  `result.json`, for example 2 in DTPLYR-1); that is outside the verdict. This is a
  looser standard than "the whole suite passes" and has not been confirmed as the
  acceptance rule.
* **Provenance of the trigger names.** They were taken from the R-100 package built on
  the reference server that was later found compromised
  (`dataset/framework/projects/<Project>/trigger_tests/<n>`). There is no independent
  checksum. The only cross-check done: for all 100 cases the number of names equals
  `trigger_count` in `case.json` (140 in total).
* `fixed_minus_minimized_patch` cases (all 100): the minimized patch is applied forward
  to the fixed revision for the buggy tree. Checking `apply --reverse --check` first is
  wrong for a pure-deletion patch and left buggy equal to fixed (CLOCK-1).
* R packages were the latest available at install time, raised where needed to meet the
  lock (for example pillar >= 1.10.1), not the exact versions in the case lock.

## Files in this change

* `scripts/d4x.py`: the options above (Dart, Perl, Julia, Lua, R) and an Elixir change
  (`D4X_CONTAINER_NET=1` runs the dependency step with host networking and
  `D4X_ELIXIR_COMPILE_ENV`; the test step still uses `--network none`).
* `scripts/r_trigger_report.R`.
* `metadata/r-trigger-tests/` (100 case files and `MANIFEST.tsv` with sha256).
* `cases/lua/EV-LU-{156,172,173,174,175,176,177}/evidence/d4j_trigger.lua`.
* This file.

Nothing here changes `case.json` or any dataset patch.
