#!/bin/bash
# API 9 variant for ARKTS-046/049: 3.2 Release declarations + the old @ohos.application.Ability /
# AbilityStage declarations that exist only in the 3.2 Beta tags (the app code uses them, the ohosTest
# scaffold uses @ohos.app.ability.*, so both families are needed).
O=$HOME/d4x/arkts-sdk-full; F=$HOME/d4x/arkts-fullapi
D=$O/9b3; rm -rf $D; mkdir -p $D
for c in js native previewer toolchains linux windows; do [ -e $O/9/$c ] && cp -al $O/9/$c $D/$c; done
cp -a $O/9/ets $D/ets
for f in @ohos.application.Ability.d.ts @ohos.application.AbilityStage.d.ts; do cp $F/y3.2-Beta3/api/$f $D/ets/api/; done
# the two files import ./application/AbilityContext and ./application/AbilityStageContext
mkdir -p $D/ets/api/application
for f in AbilityContext AbilityStageContext; do [ -f $D/ets/api/application/$f.d.ts ] || cp $F/y3.2-Beta3/api/application/$f.d.ts $D/ets/api/application/ 2>/dev/null; done
mkdir -p $D/9; for c in ets js native previewer toolchains; do ln -sfn ../$c $D/9/$c; done
W=$D/ets/build-tools/ets-loader/bin/ark/build-win; [ -d $W ] && { mkdir -p $O/_disabled/9b3; mv $W $O/_disabled/9b3/; }
echo "9b3: $(ls $D/ets/api | wc -l) api entries"
