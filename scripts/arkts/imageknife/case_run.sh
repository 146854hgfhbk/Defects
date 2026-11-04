#!/bin/bash
# usage: case_run.sh <workdir_name> <sha> <side buggy|fixed> <test.patch> <source.patch|-> <Suite#test>
N="$1"; SHA="$2"; SIDE="$3"; TP="$4"; SP="$5"; TGT="$6"
W=$HOME/d4x/t03-try/$N/$SIDE; LD=$HOME/d4x/t03-try/$N/logs; mkdir -p $LD; rm -rf $W; mkdir -p $W
cd $HOME/d4x/imageknife && git archive $SHA | tar -x -C $W || exit 11
cd $W && git init -q . && git apply $TP || { echo TEST_PATCH_FAIL; exit 12; }
if [ "$SIDE" = fixed ]; then git apply --include='library/*' $SP || { echo SRC_PATCH_FAIL; exit 13; }; fi
# environment shim 1: case-insensitive FS assumption in upstream (index.ets vs Index)
[ -f library/index.ets ] && [ ! -e library/Index.ets ] && ln -s index.ets library/Index.ets
cd $HOME/d4x/t03-try
if [ -n "$SDKFIX" ]; then python3 -I $HOME/d4x/t03-try/sdkfix.py $W; fi
./build.sh $W $LD/$SIDE; [ -d $W/sharedlibrary ] && ./hsp.sh $W $LD/$SIDE
sed "s/\x1b\[[0-9;]*m//g" $LD/$SIDE-build.log | grep -E "_rc=|ERROR" | head -8
APPRC=$(grep -o "^app_rc=[0-9]*" $LD/$SIDE-build.log | cut -d= -f2); TESTRC=$(grep -o "^test_rc=[0-9]*" $LD/$SIDE-build.log | cut -d= -f2)
if [ "$APPRC" != 0 ] || [ "$TESTRC" != 0 ]; then echo "BLOCKED:BUILD app_rc=$APPRC test_rc=$TESTRC"; exit 20; fi
python3 -I t03_shim.py $W $HOME/d4x/t03-try/$N/shim-$SIDE | grep -c module.json
CLS=${TGT%%#*}
H=$HOME/d4x/arkts-toolchain/sdk/3.2/ohos-sdk/toolchains/hdc; T=127.0.0.1:55557; B=com.openharmony.imageknife; D=$HOME/d4x/t03-try/$N/shim-$SIDE
$H -t $T shell "aa force-stop $B" >/dev/null 2>&1; $H -t $T uninstall $B >/dev/null 2>&1
HSP=""; [ -f $D/sharedlibrary-shim.hsp ] && HSP=$D/sharedlibrary-shim.hsp
$H -t $T install -r $HSP $D/entry-app-shim.hap 2>&1 | grep -o "msg:.*" | cut -c1-140
$H -t $T install -r $HSP $D/entry-test-shim.hap 2>&1 | grep -o "msg:.*" | cut -c1-140
timeout 300 $H -t $T shell "aa test -b $B -m entry_test -s unittest /ets/testrunner/OpenHarmonyTestRunner -s timeout 60000 -s class $TGT" > $LD/$SIDE-test.log 2>&1
sed "s/\x1b\[[0-9;]*m//g" $LD/$SIDE-test.log | grep -E "stream=Error|OHOS_REPORT_RESULT|ResultMsg" | cut -c1-200
