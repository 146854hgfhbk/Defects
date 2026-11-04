#!/bin/bash
# Start the Oniro/OpenHarmony 6.1 emulator WITH a virtio-gpu display (UiTest/window manager need it).
# usage: arkts_emulator_start.sh [hdc_port=55556] [serial_port=4445] [vnc_display=1]
HP=${1:-55556}; SP=${2:-4445}; VD=${3:-1}
T=$HOME/d4x/arkts-toolchain
Q=$T/qemu-root
RUN=$T/emu-run-$HP
if [ ! -f $RUN/system.img ]; then
  mkdir -p $RUN
  python3 - "$T/downloads/oniro-emulator-v6.1.zip" "$RUN" <<'PY'
import sys, zipfile, shutil, os
z = zipfile.ZipFile(sys.argv[1]); out = sys.argv[2]
for n in ("bzImage","ramdisk.img","updater.img","system.img","vendor.img","userdata.img"):
    with z.open("images/"+n) as s, open(os.path.join(out,n),"wb") as d: shutil.copyfileobj(s,d,1<<20)
PY
fi
export LD_LIBRARY_PATH=$Q/usr/lib/x86_64-linux-gnu:$Q/usr/lib
export QEMU_MODULE_DIR=$T/qemu-modules-gpu
cd $RUN
exec $Q/usr/bin/qemu-system-x86_64 -L $Q/usr/share/qemu \
  -machine q35 -accel tcg,thread=multi -cpu max -smp 4 -m 4096M -boot c \
  -nographic -vga none -device virtio-gpu-pci,xres=360,yres=720,max_outputs=1,addr=08.0 \
  -display vnc=127.0.0.1:$VD \
  -rtc base=utc,clock=host \
  -initrd ramdisk.img -kernel bzImage \
  -drive if=none,file=updater.img,format=raw,id=updater,index=0 -device virtio-blk-pci,drive=updater \
  -drive if=none,file=system.img,format=raw,id=system,index=1 -device virtio-blk-pci,drive=system \
  -drive if=none,file=vendor.img,format=raw,id=vendor,index=2 -device virtio-blk-pci,drive=vendor \
  -drive if=none,file=userdata.img,format=raw,id=userdata,index=3 -device virtio-blk-pci,drive=userdata \
  -serial telnet:127.0.0.1:$SP,server,nowait \
  -append "ip=dhcp loglevel=4 console=ttyS0,115200 init=init root=/dev/ram0 rw ohos.boot.hardware=x86_general ohos.required_mount.system=/dev/block/vdb@/usr@ext4@ro,barrier=1@wait,required ohos.required_mount.vendor=/dev/block/vdc@/vendor@ext4@ro,barrier=1@wait,required ohos.required_mount.misc=/dev/block/vda@/misc@none@none=@wait,required" \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:$HP-:55555 -device virtio-net-pci,netdev=net0
