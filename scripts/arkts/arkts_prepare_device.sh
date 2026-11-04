#!/bin/bash
# Prepare a fresh OpenHarmony emulator for the ArkTS replay:
#  remove the three pre-installed *system* apps that share bundle names with benchmark cases
#  (distributedcalc, distributedmusicplayer, etsclock) and their package-manager records.
# usage: arkts_prepare_device.sh <hdc_target> <qemu_restart_cmd...>
H=$HOME/d4x/arkts-toolchain/sdk/3.2/ohos-sdk/toolchains/hdc; T="$H -t $1"
D=/data/service/el1/public/bms/bundle_manager_service/bmsdb.db
for i in $(seq 1 30); do [ "$($T shell 'echo ok' 2>&1 | head -1)" = ok ] && break; sleep 5; done
sleep 30
$T shell "mount -o remount,rw /; mkdir -p /data/local/preinstalled-removed /data/local/bak; cp $D /data/local/bak/bmsdb.db.orig
for d in com.example.distributedcalc com.ohos.distributedmusicplayer ohos.samples.clock; do [ -d /system/app/\$d ] && mv /system/app/\$d /data/local/preinstalled-removed/; done
for b in ohos.samples.distributedcalc ohos.samples.distributedmusicplayer ohos.samples.etsclock com.example.distributedcalc com.ohos.distributedmusicplayer ohos.samples.clock; do
  sqlite3 $D \"delete from installed_bundle where KEY=\\\"\$b\\\"; delete from preinstalled_bundle where KEY=\\\"\$b\\\"; delete from first_install_bundle_info where BUNDLE_NAME=\\\"\$b\\\";\"
done; sync"
# keep the image language (zh-Hans). Several cases look controls up by their Chinese resource text
# (ARKTS-028 "animateTo 显示动画", 026/034/046/049 literal Chinese). Setting en-Latn-US in this script was wrong.
# ARKTS-004 depends on deviceInfo.deviceType !== default
$T shell "mount -o remount,rw /; sed -i s/^const.product.devicetype=default/const.product.devicetype=phone/ /system/etc/param/ohos.para; sync"
echo prepared
