#!/bin/bash
P="$1"; L="$2"
E=$HOME/d4x/cmdtools/extracted/command-line-tools
export HOME_REAL=$HOME; export HOME=$HOME/d4x/t03-try/home
export DEVECO_SDK_HOME=$E/sdk JAVA_HOME=$HOME_REAL/d4x/jdk-21 NODE_HOME=$E/tool/node
export PATH=$JAVA_HOME/bin:$E/bin:$E/tool/node/bin:$PATH
cd "$P" || exit 90
hvigorw --mode module -p module=sharedlibrary@default -p product=default --no-daemon assembleHsp > $L-hsp-build.log 2>&1; echo hsp_rc=$?
