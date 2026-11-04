#!/usr/bin/env python3
"""Restore symlinks (and exec bits) that were flattened when the OpenHarmony SDK zips were unpacked.

The official ohos-sdk zips store symlinks (native/llvm/bin/clang -> clang-15 ...). An extractor
that ignores the unix mode writes them as tiny text files holding the target name, so
`clang` fails with "Permission denied". This script reads each zip under <sdk>/linux/*.zip,
and for every symlink entry replaces the stub file with a real symlink, and for every regular
entry restores the unix exec bit.
usage: arkts_fix_sdk_symlinks.py <sdk-root> [<sdk-root> ...]    (root contains linux/*.zip)
"""
import os, stat, sys, zipfile

def fix(root):
    zdir = os.path.join(root, "linux")
    n_sym = n_exec = 0
    for z in sorted(os.listdir(zdir)):
        if not z.endswith(".zip"):
            continue
        zf = zipfile.ZipFile(os.path.join(zdir, z))
        for info in zf.infolist():
            mode = info.external_attr >> 16
            path = os.path.join(root, info.filename)
            kind = stat.S_IFMT(mode)
            if kind == stat.S_IFLNK:
                target = zf.read(info).decode()
                if os.path.islink(path) and os.readlink(path) == target:
                    continue
                if os.path.lexists(path):
                    if os.path.isdir(path) and not os.path.islink(path):
                        continue
                    os.remove(path)          # also unlinks hard links made by cp -al, only this name
                os.makedirs(os.path.dirname(path), exist_ok=True)
                os.symlink(target, path)
                n_sym += 1
            elif kind == stat.S_IFREG and (mode & 0o111) and os.path.isfile(path) and not os.access(path, os.X_OK):
                os.chmod(path, os.stat(path).st_mode | 0o111)
                n_exec += 1
    print(f"{root}: symlinks restored={n_sym} exec bits restored={n_exec}")

for r in sys.argv[1:]:
    fix(r)
