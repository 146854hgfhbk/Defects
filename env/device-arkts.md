# ArkTS device guide

**Cases: 50**  
**Status: `DEVICE_REQUIRED`**

ArkTS cases cannot be reproduced by installing software alone. They require:

1. **OpenHarmony/HarmonyOS SDK** matching the case's API level.
2. **Authorized device or emulator** with a working `hdc` connection.
3. **Signing material** accepted by the device.
4. **KVM/HDC/device bridge** when using an emulator.
5. The case's **HAP bundle** and test runner.

The dataset records build/sign evidence and, for some cases, `device_test=NOT_RUN`. A PASS in the ledger may mean a target-level build/sign differential, not a full on-device replay. Read `case.json` carefully.

## Minimal setup

```bash
# SDK
export OHOS_SDK="$HOME/d4x/ohos-sdk"
export PATH="$OHOS_SDK/toolchains:$PATH"

# device
hdc list targets
hdc shell param get const.product.model
```

Then use the case's `build_commands` and `runner` from `case.json`.

## What cannot be shipped

- Device identity/state
- Account-provisioned signing certificates
- Vendor SDK components with redistribution restrictions

These must be obtained by the reproducer. The repository only provides the case metadata and build/sign commands.

## Honest status

Do not claim "all 50 ArkTS cases are reproducible from this repository". The correct status is:

```text
DEVICE_REQUIRED — SDK/device/signing are external prerequisites.
```

If you have a device lab, record the device model, OS build, SDK version, signing mode, and `hdc` output with your reproduction report.
