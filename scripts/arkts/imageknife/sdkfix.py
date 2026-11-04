# Build-config shim for baselines that pin hvigor 4.x / API 11 (declared in case metadata, applied identically to buggy and fixed).
# usage: sdkfix.py <project_dir>
import re, sys, os, glob
W = sys.argv[1]
p = os.path.join(W, "hvigor/hvigor-config.json5"); s = open(p).read()
s2 = re.sub(r'"hvigorVersion"\s*:\s*"[^"]*",\s*"dependencies"\s*:\s*\{[^}]*\},', '"modelVersion": "5.0.0",\n  "dependencies": {\n  },', s, count=1)
open(p, "w").write(s2); print("hvigor-config changed:", s != s2)
p = os.path.join(W, "build-profile.json5"); s = open(p).read()
s2 = re.sub(r'("(?:compileSdkVersion|compatibleSdkVersion)"\s*:\s*)"?[0-9][0-9.]*(?:\([0-9]+\))?\"?(,?)',
            lambda m: m.group(1) + '"5.0.0(12)"' + (m.group(2) or ''), s)
s2 = re.sub(r'("runtimeOS"\s*:\s*)"[^"]*"', r'\1"HarmonyOS"', s2)
# HarmonyOS mode rejects armeabi-v7a; drop the entry (and a following comma if any)
s2 = re.sub(r'\s*"armeabi-v7a"\s*,?', '', s2)
s2 = re.sub(r',(\s*[\]}])', r'\1', s2)
open(p, "w").write(s2); print("build-profile changed:", s != s2)
# oh-package.json5 of 4.x-era projects lack modelVersion; hvigor 5 refuses to build them without it.
for rel in ("oh-package.json5", "entry/oh-package.json5", "library/oh-package.json5", "sharedlibrary/oh-package.json5"):
    p = os.path.join(W, rel)
    if not os.path.isfile(p): continue
    s = open(p).read()
    if '"modelVersion"' in s:
        s2 = re.sub(r'"modelVersion"\s*:\s*"[^"]*"', '"modelVersion": "5.0.0"', s, count=1)
        if s2 != s:
            open(p, "w").write(s2); print("modelVersion unified:", rel)
        continue
    s2 = s.replace("{", '{\n  "modelVersion": "5.0.0",', 1)
    open(p, "w").write(s2); print("modelVersion added:", rel)


# HarmonyOS mode rejects armeabi-v7a in any module's build-profile.json5 (e.g. the vendored gpu_transform module).
for bp in glob.glob(os.path.join(W, "**", "build-profile.json5"), recursive=True):
    if "node_modules" in bp or ".hvigor" in bp:
        continue
    t = open(bp).read()
    if "armeabi-v7a" not in t:
        continue
    t2 = re.sub(r'\s*"armeabi-v7a"\s*,?', '', t)
    t2 = re.sub(r',(\s*[\]}])', r'\1', t2)
    open(bp, "w").write(t2)
    print("abiFilters cleaned:", os.path.relpath(bp, W))
