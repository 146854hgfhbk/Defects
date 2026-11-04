#!/bin/bash
# Run the OpenHarmony emulator with KVM inside a container (the host user cannot open /dev/kvm,
# but docker --device gives root in the container access to it).
# usage: arkts_emulator_kvm.sh [hdc_port=55557] [image_dir]
HP=${1:-55557}
IMG=${2:-$HOME/d4x/arkts-toolchain/emu-run-kvm}
T=$HOME/d4x/arkts-toolchain
if [ ! -f $IMG/system.img ]; then
  mkdir -p $IMG
  python3 - "$T/downloads/oniro-emulator-v6.1.zip" "$IMG" <<'PY'
import sys, zipfile, shutil, os
z = zipfile.ZipFile(sys.argv[1]); out = sys.argv[2]
for n in ("bzImage","ramdisk.img","updater.img","system.img","vendor.img","userdata.img"):
    with z.open("images/"+n) as s, open(os.path.join(out,n),"wb") as d: shutil.copyfileobj(s,d,1<<20)
PY
fi
if ! docker image inspect d4x-ohos-emu:1 >/dev/null 2>&1; then
  docker build -q -t d4x-ohos-emu:1 - <<'DF'
FROM ubuntu:24.04
RUN apt-get update -qq && apt-get install -y -qq qemu-system-x86 && rm -rf /var/lib/apt/lists/*
DF
fi
docker rm -f d4x-ohos-emu-$HP >/dev/null 2>&1
exec docker run --rm --name d4x-ohos-emu-$HP --device /dev/kvm --network host -v $IMG:/img -w /img d4x-ohos-emu:1 \
  qemu-system-x86_64 -machine q35 -accel kvm -cpu host -smp 6 -m 4096M -boot c \
  -nographic -vga none -device virtio-gpu-pci,xres=${XRES:-360},yres=${YRES:-720},max_outputs=1,addr=08.0 \
  -display none -rtc base=utc,clock=host \
  -initrd ramdisk.img -kernel bzImage \
  -drive if=none,file=updater.img,format=raw,id=updater,index=0 -device virtio-blk-pci,drive=updater \
  -drive if=none,file=system.img,format=raw,id=system,index=1 -device virtio-blk-pci,drive=system \
  -drive if=none,file=vendor.img,format=raw,id=vendor,index=2 -device virtio-blk-pci,drive=vendor \
  -drive if=none,file=userdata.img,format=raw,id=userdata,index=3 -device virtio-blk-pci,drive=userdata \
  -append "ip=dhcp loglevel=4 console=ttyS0,115200 init=init root=/dev/ram0 rw ohos.boot.hardware=x86_general ohos.required_mount.system=/dev/block/vdb@/usr@ext4@ro,barrier=1@wait,required ohos.required_mount.vendor=/dev/block/vdc@/vendor@ext4@ro,barrier=1@wait,required ohos.required_mount.misc=/dev/block/vda@/misc@none@none=@wait,required" \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:$HP-:55555 -device virtio-net-pci,netdev=net0 -serial null
