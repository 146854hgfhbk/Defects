import sys, os, stat, zipfile
src, dst = sys.argv[1], sys.argv[2]
os.makedirs(dst, exist_ok=True)
root = os.path.realpath(dst)
z = zipfile.ZipFile(src)
bad = 0; n = 0; links = 0
for i in z.infolist():
    p = os.path.realpath(os.path.join(root, i.filename))
    if not (p == root or p.startswith(root + os.sep)):
        print("REJECT traversal:", i.filename); bad += 1; continue
for i in z.infolist():
    if bad: break
    out = os.path.join(root, i.filename)
    mode = i.external_attr >> 16
    if i.is_dir():
        os.makedirs(out, exist_ok=True); continue
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if stat.S_ISLNK(mode):
        tgt = z.read(i).decode()
        if os.path.lexists(out): os.remove(out)
        os.symlink(tgt, out); links += 1
    else:
        with z.open(i) as f, open(out, "wb") as g:
            while True:
                b = f.read(1 << 20)
                if not b: break
                g.write(b)
        os.chmod(out, (mode & 0o777) or 0o644)
    n += 1
print("files", n, "symlinks", links, "rejected", bad)
