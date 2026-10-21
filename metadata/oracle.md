# Oracle format

`metadata/oracle.jsonl` contains one row per active case. It is the machine-readable expected outcome, not an independent verification result.

```json
{
  "schema_version": 1,
  "case_id": "DART-101",
  "language": "dart",
  "expected": {"buggy": "FAIL", "fixed": "PASS"},
  "trigger": {
    "tests": ["AnsiX checkAnsiSupport ..."],
    "command": ["dart", "test", "--reporter=json"]
  },
  "timeout_seconds": 1200,
  "baseline_failures": [],
  "declared_status": "PASS",
  "oracle_level": "DECLARED",
  "source": "cases/dart/DART-101/case.json",
  "notes": "Derived from case.json; not an independent clean-room run."
}
```

## Levels

| Level | Meaning |
|---|---|
| `DECLARED` | derived from the case's declared trigger/expected failure |
| `EVIDENCED` | backed by a fresh replay bundle in `evidence/` |
| `STALE` | evidence exists but was produced with a different package/runtime version |

## Fields

- `expected.buggy` / `expected.fixed` — outcome contract
- `trigger.tests` — declared trigger test(s), file(s), or selector
- `trigger.command` — command declared by the case, when available
- `timeout_seconds` — per-case timeout, default 1800
- `baseline_failures` — allowed non-trigger failures
- `declared_status` — ledger status (`PASS`, `PARTIAL`, `BLOCKED`, ...)

## Use

```bash
python scripts/d4x.py oracle DART-101
```

A case is not "independently reproduced" merely because it has an oracle row. See `docs/REPRODUCIBILITY.md`.
