# Replay notes: ArkTS (50 cases)

Replay of the 50 ArkTS cases on one Linux host (24 cores, 122 GB RAM, Docker, no root) against an
OpenHarmony 6.1 emulator that runs inside a container with KVM. Written 2026-11-04.

PASS means: the declared trigger test fails on the buggy side and passes on the fixed side
(`FAIL_AS_EXPECTED` + `PASS`). The trigger is the `aa test` command recorded in `case.json`.

## Result

| | Cases |
|---|---:|
| PASS, stable two-state (40 original + 2 replacements) | 42 |
| timing-dependent: pass under `D4X_ARKTS_DELAY_SCALE=3`, not stable | 8 |
| not discriminating | 0 (030 and 033 were replaced on 2026-11-04) |

PASS: 001 002 003 004 005 006 007 008 009 011 013 014 015 016 017 018 019 020 021 022 023 024 025 026 027 028 029 030 031 033 034 036 037 038 040 041 044 045 046 047 048 049 (030 and 033 are the 2026-11-04 replacements).
Timing-dependent, not counted as PASS: 010 012 032 035 039 042 043 050.

28 of the PASS results (001 002 003 005 007 008 011 013 015 017 019 020 021 022 023 024 027 029 031 036 037 038 040 041 044 045 047 048) were obtained on the TCG emulator before the KVM emulator existed;
20 (004 006 009 010 012 014 016 018 025 026 028 032 034 035 039 042 043 046 049 050) on the KVM emulator. 8 of the KVM
results needed the test waits multiplied by 3 (`D4X_ARKTS_DELAY_SCALE=3`, see Step 3).

The earlier status in `env/device-arkts.md` ("DEVICE_REQUIRED, nothing run") is out of date. The
sections below say what a replay needs, what each case needed on top of the generic setup, and which
cases did not reach PASS and why.

## What you need

* Linux x86_64, Docker, about 120 GB free disk (SDKs 30 GB, emulator image 5.5 GB per copy, each case
  checkout about 1 GB while it runs), 8 GB RAM for the emulator.
* Network to `repo.huaweicloud.com` (SDK packages), `codeload.github.com` (API declarations, emulator
  image), `registry.npmjs.org` and `repo.harmonyos.com/npm` (hvigor and hypium dependencies).
  `gitee.com` was not reachable from the replay host and is not needed: the source repository is fetched
  through the mirror recorded in `case.json`.
* The emulator needs `/dev/kvm` only for speed. A user who cannot open `/dev/kvm` can still use KVM
  through `docker run --device /dev/kvm` (the container user is root). Without KVM the emulator runs
  with TCG and boots in about 4 minutes instead of 20 seconds, and the timing-sensitive cases are less stable.

## Step 1: the SDKs

The official `ohos-sdk-windows_linux-public.tar.gz` packages are not enough for a build. Four things
are wrong in them; each one was the single cause for the cases listed.

| Problem | Symptom | Cases | Fix |
|---|---|---|---|
| `ets/api` lacks many `.d.ts` files (e.g. `@ohos.distributedHardware.deviceManager` has no `DeviceInfo`, no `ServiceExtensionAbility`) | `Namespace '...' has no exported member`, `Cannot find module '@ohos....'`, `arkts-no-any-unknown` | 002, 006, 008, 011, 013, 014, 019, 020, 025, 026, 028 and others | overlay `api/` from `github.com/openharmony/interface_sdk-js` tag `OpenHarmony-v{3.2,4.0,4.1,5.0.0}-Release`, except the directories `common` and `config` |
| `ets-loader/declarations/index-full.d.ts` references component declarations that are not in the package (`form_component.d.ts` and 4 to 11 more) | `Cannot find name 'FormComponent'` | 006, 014, 039, 042 | copy them from `api/@internal/component/ets` of the same tag |
| the zips contain symbolic links (`native/llvm/bin/clang -> clang-15`), unpacked as 8-byte text files | `CMake ... is not able to compile a simple test program`, `Permission denied` | 017, 048 | `arkts_fix_sdk_symlinks.py` restores them from the zips |
| `ets-loader/bin/ark` holds both `build` and `build-win`; the loader picks `build-win` when it exists | `es2abc.exe: Exec format error` | all API 9 and 10 cases that reach the ABC step | move `build-win` away |

Two layout rules of `hvigor`:

* For API 9 (hvigor 1.x, 2.0) the SDK root must contain `<api>/{ets,js,native,previewer,toolchains}`
  next to the flat directories, otherwise hvigor decides the SDK is missing and tries to download one
  (`Sdk download failed`). Hard links (`cp -al`) work, plain symbolic links for `ets` itself do not.
* ARKTS-046 and 049 are old projects (`package.json`, `@ohos/hvigor` 1.2.2, no `hvigor/` directory).
  Their SDK root must be `<root>/<component>/<version>/`, the build is `npm install` then
  `node_modules/.bin/hvigor`, and the code imports `@ohos.application.Ability`, which exists only in the
  3.2 Beta declarations (tag `OpenHarmony-v3.2-Beta3`). The script builds a separate `9b3` SDK for them.

`scripts/arkts/arkts_setup_sdks.sh` does all of this from the four unpacked packages.

The scripts in `scripts/` were written for one host and still contain its paths: everything lives under
`$HOME/d4x` (SDKs in `arkts-toolchain/sdk/<ver>`, Node 16.20.2 in `node-v16.20.2`, JDK 21 in `jdk-21`,
the hypium 1.0.6 package in `hypium-pack`), the repository checkout is `/home/yifeipei/tools/Defects`,
and the runner reads the git object store of an earlier `d4x.py checkout` of ARKTS-001
(`replay-20261031/ARKTS-001/repo.git`). Change the constants at the top of `arkts_bulk_runner.py` and the
`$HOME/d4x` prefix in the shell scripts before using them elsewhere. They were not tested on another host.

## Step 2: the emulator

`scripts/arkts/arkts_emulator_kvm.sh <port>` starts the Oniro emulator image (OpenHarmony 6.1, API 23)
with QEMU 8.2 in a container. The image needs a `virtio-gpu-pci` device. Without it there is no
`/dev/dri`, the window manager reports `get display failed`, and every test that calls
`getCurrentTopAbility` or UiTest fails (ARKTS-003, 004, 007, 010, 016, 023, 027, 050 first showed this).

`scripts/arkts/arkts_prepare_device.sh <target>` then changes the image:

* removes the three pre-installed system apps `ohos.samples.distributedcalc`,
  `ohos.samples.distributedmusicplayer` and `ohos.samples.etsclock`
  (`/system/app/com.example.distributedcalc`, `com.ohos.distributedmusicplayer`, `ohos.samples.clock`)
  and their rows in `bmsdb.db`. A system app cannot be uninstalled and a same-named debug build is
  rejected with `install sign info inconsistent` (9 cases: 005, 009, 011, 015, 019, 034, 043, 044, 047).
* sets `const.product.devicetype=phone` in `/system/etc/param/ohos.para`. The image reports `default`;
  ARKTS-004's fix is `deviceType !== 'default'`, so on `default` the fixed side fails as well.
* The device must be restarted after the second change.
* Leave the system language alone. The image boots as `zh-Hans` and the tests depend on it: they look
  controls up by their Chinese resource text (ARKTS-028 `animateTo 显示动画`, 006 `弹窗`, the permission
  button `允许` in 025/026/034, literal Chinese in 046/049). An earlier version of this script set the
  language to English; that made 028, 006, 025, 026, 034, 046 and 049 fail on the fixed side, and they
  passed once `zh-Hans` was restored. After changing any device-wide setting, rerun a case that already
  passed.

## Step 3: the runner

`scripts/arkts/arkts_bulk_runner.py` is the ArkTS runner used here. It reads the case files of the repository
and writes `result.json` and a `cases.tsv`. It does what `d4x.py` does for the other languages and adds the
steps that ArkTS needs.

For the timing-dependent cases on the recorded emulator, set the delay scale explicitly when reproducing:

```bash
export D4X_ARKTS_DELAY_SCALE=3
python3 scripts/arkts/arkts_bulk_runner.py \
  --case ARKTS-010 --case ARKTS-012 --case ARKTS-032 --case ARKTS-035 \
  --case ARKTS-039 --case ARKTS-042 --case ARKTS-043 --case ARKTS-050
```

Run this after the SDK and emulator preparation above and after adapting the runner's host-specific paths.
The runner records the factor and changed files for each side in `result.json` under `delay_scale`.
This setting modifies waits in the test sources on both sides; it does not guarantee a stable result.
Check both sides and repeat runs as described in "Timing-dependent cases" before counting a case as PASS.
The ImageKnife replacements ARKTS-030 and ARKTS-033 use the separate procedure below.

The runner also performs these steps:

* builds the app and the `ohosTest` HAP with the case's hvigor, installs both, runs the recorded
  `aa test` command, and parses `OHOS_REPORT_RESULT`.
* `@ohos/hypium` 1.0.6 is injected from the recorded package into `oh_modules`.
* local dependencies of the lock file (`environment.lock.json`: `local_file`, `dependency_resource_compat`)
  are applied: library directories are copied to `oh_modules/@ohos/...` and their string and media
  resources merged (008, 020, 025, 026, 028, 030, 031, 032, 035, 040, 041, 048).
* `test.patch` of 021, 022, 026, 032, 037, 043, 047 has paths relative to the project directory, not to the
  repository root; the runner rewrites the path prefix.
* 046 and 049 have `project_root` without the leading `code/SuperFeature/`.
* The test command is rebuilt: several classes must be given as ONE comma separated value to
  `-s class`. Separated by spaces, `aa test` runs only the first (that made 009, 011, 018, 019
  look like "buggy passes"). A test name with spaces (006, 014) is rejected by hypium's class
  filter (`/^[A-Za-z][\w#,.]*$/`); it is passed as `-s suite <Suite> -s itName '<name with spaces>'`.
  `-s timeout 60000` is added: hypium's default of 5000 ms is too short for a UI test.
* If the buggy side starts the target test and the app process then dies (`App died`, no
  `OHOS_REPORT_RESULT`), that is recorded as the expected failure (ARKTS-016).
* `D4X_ARKTS_DELAY_SCALE=<n>` multiplies the waits of the UI tests (see "Test waits").
* The runner stops when less than 8 GB is free, and deletes both checkouts after each case. A full
  disk turned 27 later cases into BLOCKED in one run before this was added.

## Replacement of ARKTS-030 and ARKTS-033 (2026-11-04)

Both cases were replaced, not repaired: their triggers could not separate the two revisions on this emulator
(030's assertion compares dialog bounds with the display size, which cannot see an in-screen overlap with the
home-indicator strip; 033 never found the header at 360x720 and passed on both sides at 360x1280).

The two replacements are ImageKnife cases, both replayed two-state on the same emulator:

| New case | Upstream | Fix | Trigger |
|---|---|---|---|
| ARKTS-030 | `openharmony-tpc/ImageKnife` PR #423, base `95ffcb9e` | `MemoryLruCache.put`: `size <= 0 && ...` -> `\|\|` | `MemoryLruCacheOversizeTest#rejectsSingleItemAtMemoryLimit` |
| ARKTS-033 | `openharmony-tpc/ImageKnife` PR #227, base `d1527135` | `ImageKnifeDispatcher.dispatchNextJob` only dispatches progress-state requests | `DispatchProgressQueueTest#dispatchNextJobSkipsDestroyedRequestsUntilProgressRequest` |

Both are unit-level hypium tests (no UiTest, no screen geometry). Evidence: `evidence/ARKTS-030/`,
`evidence/ARKTS-033/` (result.json plus the buggy/fixed test logs).

These two need a different toolchain from the rest of the suite: HarmonyOS command-line-tools
`5.0.3.906` (SDK 5.0.0(12), hvigor 5.8.9, ohpm), not the assembled `arkts-sdk-full`. The per-case
`environment.lock.json` records the toolchain and the four environment shims that were applied
identically to both sides:

* S1 `library/Index.ets -> index.ets` (the test imports `@ohos/imageknife/Index`; the file is `index.ets`);
* S2 after packaging, `module.json` gets `compileSdkType=OpenHarmony` and `targetAPIVersion=12`, because the
  emulator image enforces code-signature only for HarmonyOS-typed packages and has no fs-verity;
* S3 `aa test ... /ets/testrunner/OpenHarmonyTestRunner -s timeout 60000`;
* S4 (ARKTS-033 only) the baseline pins hvigor 4.0.2 / API 11; its build files were upgraded to
  modelVersion 5.0.0 / SDK 5.0.0(12) identically on both sides.

### Getting the toolchain and building the two cases

The HarmonyOS command-line-tools package is not on `repo.huaweicloud.com` (`harmonyos/sdk`, `ohpm`, `os` and
`develop_tools` were checked) and the official download needs a Huawei account. The replay used a third-party
re-upload, `csukuangfj/harmonyos-commandline-tools` on Hugging Face, file
`commandline-tools-linux-x64-5.0.3.906.zip` (3,225,154,486 bytes, sha256
`c6fe61299e1b05e4023e643a319ee74c3eb369af7edecd5c3f1795b16f9db6af`). The sha256 equals the LFS hash that
repository lists; it was **not** compared with a checksum published by Huawei. `huggingface.co` was not
reachable from the replay host, `https://hf-mirror.com/csukuangfj/harmonyos-commandline-tools/resolve/main/<file>`
was.

Unpack it with an extractor that keeps symlinks and file modes and rejects paths outside the target
(`scripts/arkts/imageknife/extract_zip.py`; the host had no `unzip`). The package carries
`sdk/default/hms/ets/api/device-define/phone.json` and `2in1.json`. The OpenHarmony SDK used for the other 48
cases has no such files, and without them `SyscapTransform` stops with "The intersection of the system
capability sets configured for multiple devices is empty" for any module that declares both `phone` and `2in1`.

Build environment:

* `DEVECO_SDK_HOME=<unpacked>/command-line-tools/sdk`; `command-line-tools/bin` and `command-line-tools/tool/node/bin`
  on `PATH`.
* `JAVA_HOME` must point to a JDK (21 was used). The package has none, and `PackageHap` fails with
  `spawn java ENOENT` without it.
* `HOME` set to a scratch directory, so hvigor and ohpm caches do not leak into other cases.
* ohpm registry `https://ohpm.openharmony.cn/ohpm/`.

Steps per side: `ohpm install --all`; `hvigorw --mode module -p module=entry@default -p product=default
--no-daemon assembleHap`; the same with `module=entry@ohosTest`; when the project has a `sharedlibrary` module
(ARKTS-030), `-p module=sharedlibrary@default assembleHsp`. Then apply S2 to the built packages, install the
HSP and HAP with `hdc`, and run the `aa test` command (S3).

The scripts are in `scripts/arkts/imageknife/` (`build.sh`, `hsp.sh`, `case_run.sh`, `sdkfix.py` = S4,
`t03_shim.py` = S2, `extract_zip.py`). They were written under the staging names T03 (= ARKTS-030) and T04
(= ARKTS-033), hard-code `$HOME/d4x` and the emulator at `127.0.0.1:55557`, and have not been run on another
host. `case_run.sh` stops with `BLOCKED:BUILD` when either build fails; an earlier version went on to install
and test, which produced a failure that did not come from the case.

Routes that were tried and did not work (package signing, dropping the native libraries, turning the HSP into
a HAR, `runtimeOS: OpenHarmony`) and one rejected candidate, ImageKnife PR #319, are in
`evidence/NEGATIVE_RESULTS_ARKTS_030_033.md`. Each replacement was run three times per side with the same
result.

Limits to keep in mind: S2 rewrites package metadata after the build, so the replay shows the same ArkTS
logic failing and passing on an OpenHarmony API-12 package, not on a HarmonyOS-typed package. The 48 original
cases were not re-run with this toolchain; they use the older runner and SDK, which were left unchanged.

## Timing-dependent cases

010, 012, 032, 035, 039, 042, 043 and 050 do not have a stable pass. With `D4X_ARKTS_DELAY_SCALE=3` each
produced `FAIL_AS_EXPECTED` + `PASS` once (07:00-07:30 on 2026-11-04), but repeats are not reliable: the
fixed side intermittently reports `Component not exist`, because the `aa test` TestAbility window and the
application window compete for focus while UiTest is querying the component tree. Scaling the waits makes the
window the test wants more likely to be current, not guaranteed; 043 is the mirror image (with the shipped
waits both sides pass, with x3 the buggy side fails), so its differential may also be a timing artefact.

They are therefore excluded from the PASS list above until the focus race is fixed.

### What the one passing run shows for each of the eight

Read from the saved buggy and fixed test logs of the passing run (v15 for seven, v16 for 050). Each case was
run once in this configuration and, by decision on 2026-11-04, was not repeated.

| Case | buggy side | relation to the fix |
|---|---|---|
| 010 | assertion `expect 1 equals 0` | value assertion, fixed side clean |
| 012 | assertion `expect 3 equals 0` | value assertion, fixed side clean |
| 032 | assertion `expect false, actualValue is true` | value assertion, fixed side clean |
| 042 | assertion `expect true, actualValue is false` | value assertion, fixed side clean |
| 043 | assertion `expect true, actualValue is false` | value assertion; with the shipped waits the buggy side passed in v3, v5, v8 and v14 |
| 039 | `Component not exist`, text `-40` | the fix adds `OFFSET_MIN = -40`, so the text cannot exist before it |
| 050 | `Component not exist`, text `2026/11/04` | the fix multiplies `dateAdded` by 1000, so the date is wrong before it |
| 035 | `App died`, no assertion | the fix title is a crash fix and changes the emitter data to a plain object; the crash reason is not in the saved logs |

For 039 and 050 the message is the same one the focus race produces, so one buggy-side log cannot tell the
defect from the race; the direction of the evidence agrees with the defect. For 043 the explanation that the
x3 wait gives `terminateSelf` in `onBackground` enough time to take effect (the test waits 1500 ms after
`doAbilityBackground`) fits the code but was not tested.

## Test waits: the cause of eight cases

ARKTS-010, 012, 032, 035, 039, 042, 043 and 050 failed on the fixed side with `Component not exist`,
`Cannot read property ... of null` or `Calling WaitAbilityMonitor failed` (043: the buggy side passed). All
of them passed after the waits in their `ohosTest` sources were multiplied by 3 and nothing else changed:

* On this emulator a freshly started app shows its window about 2 s after `startAbility`
  (a poll with `uitest dumpLayout` found the first control after 1.9 to 2.0 s). The tests wait 1 s, 1.2 s or 2.4 s
  and then look for a control. While the window list is still changing UiTest answers `Component not exist`
  although the control is there (a layout dump taken later shows it).
* Evidence on ARKTS-012: with the waits 1000 -> 6000 ms and 200 -> 1500 ms, 3 of 3 runs passed on the fixed
  build and 3 of 3 failed on the buggy build (`expect 3 equals 0`). With the shipped waits, 0 of 6 passed on KVM.
  Repeating the test five times, pre-launching the app, stopping it first, bringing the launcher to the front,
  `aa test -w 20` and KVM instead of TCG did not help.
* ARKTS-050 uses a constant named `TIME_OUT = 1000` for `waitAbilityMonitor`; the scaling covers that name too.
* ARKTS-043: with the shipped waits both sides pass; with the waits multiplied by 3 the buggy side fails and the
  fixed side passes. Why the shipped 1200 ms does not show the failure was not investigated (the buggy build does
  contain `terminateSelf()` in `onBackground`, checked in the HAP).

`D4X_ARKTS_DELAY_SCALE=3` makes the runner rewrite `delayMs(<int>)` and constants named `*DELAY*`, `*WAIT*`,
`*SLEEP*`, `*TIMEOUT*`/`*TIME_OUT*` in the `ohosTest` sources of both sides. Assertions and the application are
not touched, the files changed are listed under `delay_scale` in `result.json`. This is a runner change, not the
dataset's own test.

## What this does not show

* One run of all 50 with the final runner has not been made; the table merges the latest result of each
  case from several runs.
* Waits scaled by 3 are a property of this emulator. A real device, or a faster emulator, may need none.
* The 28 cases that passed on the TCG emulator were not repeated on the final KVM emulator. That
  emulator differs from the one they passed on: device type `phone` instead of `default`, and KVM instead
  of TCG. No case is known to depend on the old values, but this was not checked.
* Attempts: the runner can repeat a test (`D4X_ARKTS_ATTEMPTS`). A repeat never turned a failing case into
  a passing one here; the longer waits did.
* `oracle_level` is DECLARED: the buggy/fixed result is the recorded trigger, not an independent verdict.
* The three removed system apps and the changed device type mean the emulator is not the stock image.
