# ARKTS-030 / ARKTS-033 replacement: negative results and rejected routes (2026-11-04)

ARKTS-030 is ImageKnife #423 and ARKTS-033 is ImageKnife #227; they replace the two cases whose buggy side also passed on the emulator (see docs/REPLAY_ARKTS.md).

Recorded so nobody retries them blindly. All on the KVM emulator 55557 (kernel 6.6.101, /data ext4 without verity).

1. Signing the packages does not help. Debug-type profile from the SDK template fails (`CheckDeviceID: device-id list is empty`; the emulator's `bm get -u` returns no UDID). A release-type profile signed with the public OpenHarmony test CA passes HapVerify, but install then fails in code-signature enforcement: with a code-sign block `-256` (`IsSupportFsVerity errno 22`), with `-signCode 0` `-772`.
2. Dropping the native libs (`nativeLib.filter.excludes **/*.so`) and converting `sharedlibrary` from HSP to HAR both built fine but did NOT fix the install failure. They are not part of the final recipe. Only the module.json SDK metadata matters (bisected: compileSdkType + targetAPIVersion; vm version, deviceTypes, API number alone do nothing).
3. `compileSdkType` removed or set to OpenHarmony while targetAPIVersion stays 50000012 fails with "older sdk version in the device" (9568297).
4. The three emulators 55555/55556/55557 behave identically for these packages.
5. Switching `runtimeOS` to OpenHarmony in build-profile.json5 needs OHOS_BASE_SDK_HOME and would use the OpenHarmony device-define set, which has no phone/2in1 (the original blocker). Not pursued.
6. Rejected candidate, ImageKnife PR #319 (file cache custom path): test fails on the buggy baseline as expected, but the app module does not compile with the HarmonyOS 5.0 SDK. `entry/.../dataShareUriLoadPage.ets` uses the legacy `@ohos.multimedia.mediaLibrary` callbacks, rejected by `arkts-no-any-unknown`. Fixing that means editing upstream sample code, so the case is BLOCKED, not accepted. (A first run of this case printed an assertion failure from the test hap alone; that was a driver bug that installed without the app hap and is void. The driver now stops on any build failure.)
7. ImageKnife PR #333 only changes sample pages (no production code) and PR #309 only changes sample dependencies, so neither is a defect case.
8. First draft of the first staged draft of ARKTS-030 (ImageKnife #423, staged as T03)/case.json had `runner: /ets/TestRunner/...` and `declared_hvigor_version: 4.1.2`; both were wrong and are corrected here.
