#!/bin/bash
# copy component declarations referenced by ets-loader/declarations/index-full.d.ts but absent in the official package
O=$HOME/d4x/arkts-sdk-full; F=$HOME/d4x/arkts-fullapi
for p in "9 3.2" "10 4.0" "11 4.1" "12 5.0.0"; do set -- $p; api=$1; ver=$2
  D=$O/$api/ets/build-tools/ets-loader/declarations; [ -d $D ] || { echo "api $api: no declarations dir"; continue; }
  S=$F/x$ver/api/@internal/component/ets
  miss=0; fix=0; left=""
  for f in $(grep -o 'path="./[A-Za-z_0-9]*\.d\.ts"' $D/index-full.d.ts | sed 's#path="./##;s#"##'); do
    if [ ! -f $D/$f ]; then miss=$((miss+1)); if [ -f $S/$f ]; then cp $S/$f $D/$f; fix=$((fix+1)); else left="$left $f"; fi; fi
  done
  echo "api $api: missing=$miss copied=$fix unresolved=[$left ]"
done
