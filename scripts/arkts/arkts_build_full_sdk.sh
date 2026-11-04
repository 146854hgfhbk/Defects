#!/bin/bash
set -e
B=$HOME/d4x/arkts-toolchain/sdk
F=$HOME/d4x/arkts-fullapi
O=$HOME/d4x/arkts-sdk-full
mkdir -p $O
# api  tag  src-ets-dir  out-name
build() {
  api=$1; ver=$2; src=$3
  dst=$O/$api
  rm -rf $dst; mkdir -p $dst
  for c in js native previewer toolchains linux windows; do [ -e $src/$c ] && cp -al $src/$c $dst/$c; done
  cp -a $src/ets $dst/ets
  mkdir -p $F/x$ver
  [ -d $F/x$ver/api ] || tar xzf $F/isj-$ver.tgz -C $F/x$ver --strip-components=1
  (cd $F/x$ver/api && for e in $(ls | grep -vE "^(common|config)\$"); do cp -a $e $dst/ets/api/; done)
  [ -d $F/x$ver/api/@internal/component/ets ] && cp -a $F/x$ver/api/@internal/component/ets/. $dst/ets/component/
  [ -d $F/x$ver/kits ] && mkdir -p $dst/ets/kits && cp -a $F/x$ver/kits/. $dst/ets/kits/
  # hvigor treats a root without <api>/{ets,js,...} as an old-layout SDK and tries to download one
  mkdir -p $dst/$api; for c in ets js native previewer toolchains; do ln -sfn ../$c $dst/$api/$c; done
  echo "api $api ($ver): api files $(ls $dst/ets/api | wc -l), component $(ls $dst/ets/component | wc -l)"
}
build 9  3.2   $B/3.2/ohos-sdk
build 10 4.0   $B/4.0/ohos-sdk
build 11 4.1   $B/4.1/ohos-sdk
build 12 5.0.0 $B/5.0.0
du -sh $O

# second gap in the official package: ets-loader/declarations/index-full.d.ts references component .d.ts files that are not shipped
bash $(dirname $0)/arkts_fix_declarations.sh
