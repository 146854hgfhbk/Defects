# usage: t03_shim.py <project_dir> <out_dir>
# Environment shim (declared in case metadata): rewrite app-level SDK metadata in module.json of the two built HAPs
# so the OpenHarmony emulator image treats them as OpenHarmony API 12 packages. No code, resource or abc is touched.
import zipfile, json, sys, os, glob, hashlib
P, O = sys.argv[1], sys.argv[2]; os.makedirs(O, exist_ok=True)
for side, pat in (("app", "entry/build/default/outputs/default/*.hap"), ("test", "entry/build/default/outputs/ohosTest/*.hap"), ("hsp", "sharedlibrary/build/default/outputs/default/*.hsp")):
    if not glob.glob(os.path.join(P, pat)): continue
    src = glob.glob(os.path.join(P, pat))[0]
    out = os.path.join(O, f"entry-{side}-shim.hap" if side != "hsp" else "sharedlibrary-shim.hsp")
    zi = zipfile.ZipFile(src); zo = zipfile.ZipFile(out, "w", zipfile.ZIP_STORED)
    for i in zi.infolist():
        d = zi.read(i.filename)
        if i.filename == "module.json":
            m = json.loads(d)
            before = {k: m["app"].get(k) for k in ("compileSdkType", "targetAPIVersion", "minAPIVersion")}
            m["app"]["compileSdkType"] = "OpenHarmony"; m["app"]["targetAPIVersion"] = 12; m["app"]["minAPIVersion"] = 12
            d = json.dumps(m).encode()
            print(side, "module.json", before, "->", {k: m["app"][k] for k in before})
        zo.writestr(i, d, compress_type=i.compress_type)
    zo.close()
    print(side, "src_sha256", hashlib.sha256(open(src, "rb").read()).hexdigest()[:16], "out", out)
