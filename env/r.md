# R environment guide

**Cases: 100**  
**Guide scope: native R 4.4.3 + per-case CRAN archive**

## Versions

All active R cases use the Ubuntu 26.04 / R 4.4.3 reference environment:

```text
R 4.4.3
Ubuntu 26.04 LTS x86_64
14 pinned R packages per case
```

The per-case lock is:

```bash
cat cases/r/BENCH-1/case.json | python -c "import sys,json; c=json.load(sys.stdin); print(c['environment_file'])"
```

The referenced `environment_file` (for example `framework/projects/Bench/environments/ubuntu-26.04-r-4.4.3-1.json`) lists the exact package versions.

## Install R 4.4.3

On Ubuntu 26.04:

```bash
sudo apt-get update
sudo apt-get install -y r-base r-base-dev build-essential libcurl4-openssl-dev libssl-dev libxml2-dev
R --version
```

If the distro R is not 4.4.3, use the CRAN repository for Ubuntu or `rig`:

```bash
curl -Ls https://raw.githubusercontent.com/r-lib/rig/main/install.sh | sudo bash
rig add 4.4.3
rig default 4.4.3
R --version
```

## Install R packages

Read the environment JSON and install the exact versions:

```bash
python - <<'PY'
import json, glob
c=json.load(open('cases/r/BENCH-1/case.json'))
print(c['environment_file'])
PY
```

Use a CRAN snapshot/archive matching the lock. Example:

```r
install.packages("testthat", repos = "https://packagemanager.posit.co/cran/2026-09-01")
```

If the lock lists a package version no longer on CRAN, download the archived source tarball and install it explicitly:

```bash
R CMD INSTALL --library="$HOME/d4x/Rlib" pkg_1.2.3.tar.gz
```

## Build and test

R cases follow a Defects4J-style project layout:

```bash
R CMD INSTALL --library="$HOME/d4x/Rlib" .
Rscript -e 'library(testthat); test_file("tests/testthat/test-....R")'
```

Use the case's `environment_file` and project metadata; do not install the latest CRAN versions.

## Network isolation

Most R cases use a local package library and no network during replay:

```bash
unshare -n -- Rscript -e '...'
```

Install packages before isolating.

## Common failures

- `there is no package called ...` — wrong library path or missing pinned package.
- native compilation errors — missing `libcurl`/`libssl`/`libxml2` headers.
- package version drift — CRAN latest differs from the lock; use the archived tarball.
- R version mismatch — use 4.4.3, not 4.5+.
