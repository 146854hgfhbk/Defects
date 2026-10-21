# Julia environment guide

**Cases: 100**  
**Guide scope: native Julia + per-case Manifest/Project**

## Versions

| Julia | Cases (approx.) |
|---|---:|
| 1.6.7 | 7 |
| 1.8.5 | 1 |
| 1.9.1 | 1 |
| 1.10.12 | 81 |
| 1.12.7 | 10 |

Read the case:

```bash
python - <<'PY'
import json
c=json.load(open('cases/julia/JULIA-002/case.json'))
print(c['build'])
print(c['environment_lock'])
PY
```

`case.json.build.julia_version` is authoritative.

## Install

Using `juliaup`:

```bash
curl -fsSL https://install.julialang.org | sh
juliaup add 1.10.12
juliaup default 1.10.12
julia --version
```

Or use the official tarball:

```bash
export JULIA_VERSION=1.10.12
curl -fL -o /tmp/julia.tar.gz \
  "https://julialang-s3.julialang.org/bin/linux/x64/1.10/julia-${JULIA_VERSION}-linux-x86_64.tar.gz"
tar -xzf /tmp/julia.tar.gz -C "$HOME/d4x"
export PATH="$HOME/d4x/julia-$JULIA_VERSION/bin:$PATH"
```

## Per-case environment

Julia cases ship:

```text
environment/buggy/Project.toml
environment/buggy/Manifest.toml
environment/fixed/Project.toml
environment/fixed/Manifest.toml
```

Use the matching side's environment:

```bash
export JULIA_DEPOT_PATH="$HOME/d4x/julia-depot"
julia --project=environment/buggy -e 'using Pkg; Pkg.instantiate(); Pkg.precompile()'
```

Do **not** resolve a new Manifest unless the case explicitly permits it; the locked Manifest is part of the case.

## Run

```bash
julia --project=environment/buggy -e 'using Pkg; Pkg.test(; allow_reresolve=false)'
# or the case-declared trigger:
julia --project=environment/buggy trigger/trigger.jl
```

Julia cases declare a trigger script under `trigger/` and often an `upstream-tests.patch`. Use the case-declared command.

## Common failures

- `Unsatisfiable requirements` — wrong Julia version or modified Manifest.
- `Package ... not found` — depot not populated; run `Pkg.instantiate()` with network allowed first.
- Native library errors (`libopenlibm.so`) — Julia binary and glibc mismatch; use the exact tarball, not a distro Julia.
- Test order dependence — use a fresh depot/worktree per repetition.
