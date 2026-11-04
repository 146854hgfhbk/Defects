#!/bin/bash
# usage: t03_build.sh <project_dir> <logprefix>
P="$1"; L="$2"
E=$HOME/d4x/cmdtools/extracted/command-line-tools
export HOME_REAL=$HOME
export HOME=$HOME/d4x/t03-try/home; mkdir -p $HOME
export DEVECO_SDK_HOME=$E/sdk

export PATH=$E/bin:$E/tool/node/bin:$PATH
export NODE_HOME=$E/tool/node
export JAVA_HOME=$HOME_REAL/d4x/jdk-21
export PATH=$JAVA_HOME/bin:$PATH
cd "$P" || exit 90
ohpm config set registry https://ohpm.openharmony.cn/ohpm/ > $L-ohpm-config.log 2>&1
echo "== ohpm install" > $L-build.log
ohpm install --all >> $L-build.log 2>&1; echo "ohpm_rc=$?" >> $L-build.log
echo "== hvigorw app" >> $L-build.log
hvigorw --mode module -p module=entry@default -p product=default --no-daemon assembleHap >> $L-build.log 2>&1; echo "app_rc=$?" >> $L-build.log
echo "== hvigorw ohosTest" >> $L-build.log
hvigorw --mode module -p module=entry@ohosTest -p product=default --no-daemon assembleHap >> $L-build.log 2>&1; echo "test_rc=$?" >> $L-build.log
echo FINISHED >> $L-build.log
