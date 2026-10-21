# Swift ID mapping

The Swift release uses `SWIFT-Dxxx` IDs, but the package-internal `case.json` retains the original `SWIFT-xxx` / `CASES-SWIFT-xxx` ID.

`metadata/id-mapping.json` is the canonical mapping:

```json
{
  "release_case_id": "SWIFT-D003",
  "package_case_id": "SWIFT-019",
  "directory": "cases/swift/SWIFT-D003",
  "repository_url": "https://github.com/vapor/jwt.git"
}
```

Use `release_case_id` for:

- `cases/swift/<ID>/`
- `metadata/cases.jsonl`
- `metadata/oracle.jsonl`
- HF `images/manifest.json`

Use `package_case_id` only when a package script requires the historical ID.

```bash
python - <<'PY'
import json
m={e['release_case_id']:e for e in json.load(open('metadata/id-mapping.json'))['entries']}
print(m['SWIFT-D003'])
PY
```
