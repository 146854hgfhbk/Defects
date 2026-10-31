# Replay notes: Swift

Replay of the 100 Swift cases on one clean Ubuntu 24.04 host (2 vCPU, 7 GB RAM, Docker),
using `scripts/d4x.py` and the five Swift images rebuilt from `images/build/`.

## Result

| Image tag | Cases | Latest run of each case |
|---|---:|---|
| `swift-defects-validation:5.10.1-restored-20260908` | 41 | PASS |
| `swift-defects-validation:6.1-recovered-20260905` | 13 | PASS |
| `swift-defects-validation:6.2.3-recovered-20260906-v2` | 16 | PASS |
| `swift-defects-validation:6.2.3-recovered-20260906-v3-sqlite` | 18 | PASS |
| `swift-defects-validation:6.2.3-recovered-20260906-v4-openssl` | 12 | PASS |

PASS means the buggy side fails and the fixed side passes. The results come from several
runs made while `d4x` was being fixed; one single run of all 100 with the final `d4x` has
not been done.

## What you need

* Linux x86_64, Docker with Buildx, 2 or more cores, 7 GB RAM. Disk: the replay host held 109
  Docker images (Elixir images included) of about 230 GB in total; plan for the Swift images
  alone to be a large part of that.
* The five images, built from source: `cd images/build && make swift`. Their image IDs differ
  from the IDs recorded in `case.json`. `d4x` maps the recorded ID to a tag through
  `metadata/image-tags.json`, so the tags must be exactly the ones in the table above.
* Network access to GitHub (for the upstream repositories) and to the package hosts that
  SwiftPM resolves from, **during the dependency step only**. The test run itself uses
  `--network none`.
* `docker` must be callable by the user running `d4x` (the runs here used `sudo -E`).

## Step 1: resolve dependencies once, with network

A Swift case cannot build offline unless its dependencies are already in the checkout. The
repository does not ship them: the `dependencies.tar.gz` snapshots are not included, and the
`dependency_cache` that some cases ship was not used. Without this step `swift build` under
`--network none` fails with `GitShellError ... 128` and the case ends as `COMPILE_ERROR` or
`BLOCKED`; on the 5.10.1 image 22 of the 41 cases were blocked this way on the first pass.

For each case, check out both sides, put the recorded `Package.resolved` in place when it
has pins, and resolve inside the case's image:

```bash
ID=SWIFT-D042                       # case id
W=/tmp/d4x-work/swift               # work directory
IMG=$(python3 - "$ID" <<'PY'
import json, sys
tags = json.load(open("metadata/image-tags.json"))["swift"]
c = json.load(open(f"cases/swift/{sys.argv[1]}/case.json", encoding="utf-8-sig"))
print(tags[c["runtime_release"]["image_id"]])
PY
)

python3 scripts/d4x.py checkout "$ID" --work "$W" --force

for side in buggy fixed; do
  rec=cases/swift/$ID/environment/post-minimization-$side-Package.resolved
  n=$(python3 -c "import json;d=json.load(open('$rec'));print(len(d.get('pins') or d.get('object',{}).get('pins',[])))" 2>/dev/null || echo 0)
  [ -s "$rec" ] && [ "$n" != "0" ] && cp "$rec" "$W/$ID/$side/Package.resolved"
  docker run --rm --network host -v "$W/$ID/$side:/work" -w /work "$IMG" \
    bash -lc "swift package resolve"
done
```

Behind a proxy, add `-e https_proxy=... -e http_proxy=...` to `docker run`.

`Package.resolved` keeps the recorded versions only where the case recorded pins. In 48 cases
there is no `environment/post-minimization-<side>-Package.resolved` at all (SWIFT-D008, D023,
D052 to D054, D059 to D101), and 14 more have the file with no pins (SWIFT-D001,
D002, D003, D006, D007, D015, D026, D028, D038, D039, D042, D049, D055, D058). For these 62
cases SwiftPM picks the versions at resolve time. An audit found 15 passing cases whose resolved
versions differ from the recorded ones; two of them (D022, D027) were re-run with the recorded
pins and still pass, the other 13 were not re-run. A PASS therefore does not show that the
originally recorded dependency versions reproduce.

SWIFT-D060: its `dependencies.tar.gz` has a sha256 that does not match the one declared in
`case.json`, so that snapshot is not used. The case passes through the resolve step above.

## Step 2: run the case

```bash
python3 scripts/d4x.py run "$ID" --work "$W" --timeout 1800
```

`d4x` takes the work tree from step 1 (run it without `--force`, as the replay did, so the
resolved dependencies stay in place) and runs the build and test commands with
`--network none`.

Time per case: a few minutes for packages without heavy dependencies, 10 minutes and more
when SwiftPM builds `swift-syntax`.

## What `d4x` does for you

These are handled by the runner and need no option:

* Trigger patch: the one that `case.json` declares in `patches.trigger_tests.path`. Eight
  cases ship several candidates (`...-compatible`, `...-stable`), and choosing by file name
  picks the wrong one.
* `patches.build_compatibility` is applied on both sides before the trigger patch (SWIFT-D003,
  D005, D015, D024, D025, D041). D003 needs it for the OpenSSL 3 macro alias `EVP_MD_type`.
* Test discovery: `--enable-test-discovery` is added when `Tests/LinuxMain.swift` is a stub that
  asks for it, or an empty `XCTMain` (SWIFT-D042, D080, D081). If a build fails on a stale
  `LinuxMain.swift` (SWIFT-D085) the compile is retried once with the flag.
* Fixed tree: for the 47 cases with `artifacts.fixed.equals_upstream_tree == false`, the
  production patch does not apply to the upstream fix commit, so the fixed side is the base
  revision plus the trigger and production patches. `scripts/fetch_sources.py` uses the same
  revision. Cases where this was needed to get a PASS include SWIFT-D064, D065, D066, D068,
  D074, D095.
* Several trigger test names are passed as several `--filter` flags.
* `/opt/swift510/usr/bin/swift` in five cases (SWIFT-D070, D086, D089, D093, D097) is
  rewritten to `swift` inside the images.
* Clone retries: `D4X_CLONE_RETRIES` (default 5). SWIFT-D070 needed a retry.

## Cases to read with care

* SWIFT-D058 and SWIFT-D060 have a compile error as their trigger. PASS means the fixed
  side compiles ("No matching test cases were run" in the log). The runner does not check
  that the buggy-side error is at the expected source location.
* 36 cases have more than one trigger test name. On the fixed side, every name was checked
  only for SWIFT-D046. For the other 35 the buggy side already fails with the first name,
  and more names cannot change that, but one of the other trigger tests could still fail on
  the fixed side.
* The images are rebuilt, so their digests differ from the originals. The runtime versions
  match; that alone does not show the images are equivalent.
* `D4X_ENABLE_XCTEST=1` (used in the earlier validation tree for SWIFT-D052 and D059) is not
  needed: both pass without it.
