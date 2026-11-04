# Replay notes: ArkTS (50 cases)

Replay of the 50 ArkTS cases on one Linux host (24 cores, 122 GB RAM, Docker, no root) against an
OpenHarmony 6.1 emulator that runs inside a container with KVM. Written 2026-11-04.

PASS means: the declared trigger test fails on the buggy side and passes on the fixed side
(`FAIL_AS_EXPECTED` + `PASS`). The trigger is the `aa test` command recorded in `case.json`.

## Result

| | Cases |
|---|---:|
| PASS (buggy `FAIL_AS_EXPECTED`, fixed `PASS`) | 48 |
| not PASS | 2 |

PASS: 001 002 003 004 005 006 007 008 009 010 011 012 013 014 015 016 017 018 019 020 021 022 023 024 025 026 027 028 029 031 032 034 035 036 037 038 039 040 041 042 043 044 045 046 047 048 049 050.

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
steps that ArkTS needs:

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

## Cases that did not reach PASS

| Case | buggy | fixed | what was seen |
|---|---|---|---|
| ARKTS-030 | UNEXPECTED_PASS | PASS | the buggy side passes the declared trigger |
| ARKTS-033 | UNEXPECTED_PASS | PASS | on a 360x1280 screen the buggy side passes; on 360x720 the fixed side fails (see below) |

### ARKTS-030 and 033

* ARKTS-030: the test asks whether the two dialog buttons lie inside the screen. The buggy side passes it on the
  360x720 emulator, with the shipped waits and with the waits multiplied by 3. The probe values of the buggy run
  were not looked at, so the reason is not known.
* ARKTS-033: the trigger checks that the page title is not covered. On a 360x720 screen the fixed side reports
  `HEADER_DISPLACED:titleTop=-1;subtitleBottom=-1` (the title text is not found), the buggy side the same. On a
  360x1280 screen (`XRES=360 YRES=1280 arkts_emulator_kvm.sh`) the fixed side passes, and so does the buggy side.
  Neither screen size gave the expected pair.
* In both cases the test file was left as the dataset ships it. Changing a screen size or a threshold would make
  the result a different test.

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
