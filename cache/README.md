# Dependency caches

`index.json` records, for every case, which dependency cache is required and where the lock lives.

| Language | Cache kind | Status |
|---|---|---|
| Dart | pub cache | declared |
| Julia | depot + per-side Manifest | declared |
| Kotlin | Gradle/Maven cache | declared |
| Lua | LuaRocks tree | declared |
| Perl | CPAN closure | declared |
| R | CRAN library | declared |

**No large cache tarballs are committed to GitHub.** The index is the contract; use the case's lock files and the language guide to materialize the cache.

## Per-case fields

```json
{
  "case_id": "JULIA-002",
  "language": "julia",
  "cache_type": "julia-depot+manifest",
  "source": "environment/buggy/Manifest.toml,environment/fixed/Manifest.toml",
  "artifact": null,
  "status": "declared"
}
```

- `source` — the lock file(s) in the case directory
- `artifact` — optional HF path or URL to a prepared cache archive
- `status` — `declared` (recipe only), `available` (artifact exists), or `missing`

## Materialize a cache

```bash
# Julia
julia --project=environment/buggy -e 'using Pkg; Pkg.instantiate()'

# Kotlin
./gradlew --no-daemon :module:testClasses

# Dart
dart pub get

# Lua
luarocks install --tree ./lua-tree busted 2.2.0-1

# R
Rscript -e 'install.packages(readLines("requirements.txt"), repos=...)'
```

For offline replay, prepare the cache once, then mount/copy it and disable the network.

## Future artifacts

When cache archives are published, add:

```json
"artifact": "cache/julia/JULIA-002.tar.zst",
"status": "available"
```

and upload to the HF dataset under `cache/`.
