#!/bin/bash
# Build the complete ArkTS SDK set used by the Defects4X ArkTS replay.
#   input : ~/d4x/arkts-toolchain/sdk/{3.2,4.0,4.1}/ohos-sdk and 5.0.0 (official packages, unpacked)
#           ~/d4x/arkts-fullapi/isj-<ver>.tgz  (github openharmony/interface_sdk-js tags)
#   output: ~/d4x/arkts-sdk-full/{9,10,11,12} and 9b3 (API 9 with 3.2-Beta3 declarations, ARKTS-046/049)
set -e
D=$HOME/d4x
bash $D/arkts_build_full_sdk.sh                       # official package + full api/ declarations
for r in $D/arkts-toolchain/sdk/3.2/ohos-sdk $D/arkts-toolchain/sdk/4.0/ohos-sdk \
         $D/arkts-toolchain/sdk/4.1/ohos-sdk $D/arkts-toolchain/sdk/5.0.0; do
  python3 $D/arkts_fix_sdk_symlinks.py $r            # zips were unpacked without symlinks -> clang etc.
done
for a in 9 10 11 12; do python3 $D/arkts_fix_sdk_symlinks.py $D/arkts-sdk-full/$a; done
# ets-loader picks build-win when that directory exists, even on Linux -> Exec format error
for a in 9 10 11 12; do
  W=$D/arkts-sdk-full/$a/ets/build-tools/ets-loader/bin/ark/build-win
  [ -d "$W" ] && { mkdir -p $D/arkts-sdk-full/_disabled/$a; mv "$W" $D/arkts-sdk-full/_disabled/$a/; }
done
bash $D/arkts_build_beta3_sdk.sh                      # API 9 variant with old @ohos.application.Ability
W=$D/arkts-sdk-full/9b3/ets/build-tools/ets-loader/bin/ark/build-win
[ -d "$W" ] && { mkdir -p $D/arkts-sdk-full/_disabled/9b3; mv "$W" $D/arkts-sdk-full/_disabled/9b3/; }
echo SDK_SET_READY
