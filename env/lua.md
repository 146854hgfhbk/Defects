# Lua environment guide

**Cases: 100**  
**Guide scope: native Lua 5.4 + LuaRocks + Busted**

## Versions

The Lua package records per-case runtime identity in `environment.json`:

```json
{
  "lua": "5.4.8",
  "luarocks": "3.11.1",
  "busted": "2.2.0-1",
  "runtime_image": "defects4x/penlight-p3:lua54-v2",
  "runtime_image_id": "sha256:..."
}
```

Read the case:

```bash
python - <<'PY'
import json
c=json.load(open('cases/lua/EV-LU-004/case.json'))
print(json.dumps(c['manifest'], indent=2)[:2500])
print(open('cases/lua/EV-LU-004/environment.json').read())
PY
```

The `runtime_image` / `runtime_image_id` in `environment.json` is the exact reference runtime. Native Lua is supported when the versions match; otherwise use the recorded image.

## Install native Lua

```bash
sudo apt-get update
sudo apt-get install -y lua5.4 luarocks build-essential
lua -v          # Lua 5.4.x
luarocks --version
```

Install the runtime and test runner:

```bash
luarocks install busted 2.2.0-1
busted --version
```

If the case pins a different Lua/LuaRocks/Busted version, use the case's `environment.json` and `evidence/Dockerfile.*` as the recipe.

## Run

```bash
cd <case-source>
LUA_PATH="./lua/?.lua;./lua/?/init.lua;;" \
  busted --filter "<trigger filter>" <test file>
```

The trigger selector is in `case.json.manifest.trigger_selector`:

```json
{
  "selector_kind": "busted_filter",
  "test_file": "spec/utils-choose_spec.lua",
  "filter": "handles nils",
  "command": ["busted", "--filter", "handles nils", "spec/utils-choose_spec.lua"]
}
```

## Container option

If native versions do not match:

```bash
docker run --rm -it \
  -v "$PWD:/workspace" -w /workspace \
  defects4x/penlight-p3:lua54-v2 \
  busted --filter "handles nils" spec/utils-choose_spec.lua
```

Pin the digest from `environment.json`, not just the tag.

## Common failures

- `module 'pl.utils' not found` — `LUA_PATH` not set to the package layout.
- `busted: command not found` — install `busted` with the pinned LuaRocks tree.
- Native C modules fail to build — missing `build-essential`/`liblua5.4-dev`.
- Version mismatch — use the case image; Lua cases are runtime-image pinned.
