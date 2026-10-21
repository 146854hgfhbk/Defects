# Fix9 独立修复审计（2026-10-14）

本目录是对单独摘出的 9 个修复案例的证据叠加层。原始全量账本未被覆盖。

本发布快照在此叠加层上应用 R=100 发布上限；R 的 106 条来源记录中保留 canonical 顺序前 100 条，移除记录见 metadata/r-cap-removals.json 和 evidence/R-CAP-R100.md。
本轮补入 ygd 远端完成的 KOTLIN-501 strict replay-07（含 PDF readiness retry shim），以及此前已完成的 D049 和 7 个 Elixir blocker 证据；ZIP 内的 fix9 日志保持原样。

## fix9 与 blocker-repair 证据状态

| case | status | evidence grade | 结论 |
|---|---|---|---|
| ELIXIR-027 | PASS | FIX9_DIRECT_DYNAMIC | trigger pinned to test/mix/ecto_test.exs:53 (ensure started) |
| ELIXIR-030 | PASS | FIX9_DIRECT_DYNAMIC | trigger pinned to test/ecto/query/planner_test.exs:905 |
| ELIXIR-061 | PASS | FIX9_DIRECT_DYNAMIC | MIX_ENV=test mix test --trace; fixed 32 tests, 0 failures |
| ELIXIR-092 | PASS | FIX9_DIRECT_DYNAMIC | offline Hex/Rebar bootstrap is non-fatal; fixed 70 tests, 0 failures |
| KOTLIN-152 | PASS | FIX9_DIRECT_DYNAMIC | JDK 17.0.20 with Gradle 7.3.3; fixed BUILD SUCCESSFUL and buggy trigger failed |
| KOTLIN-153 | PASS | FIX9_DIRECT_DYNAMIC | JDK 17.0.20 with Gradle 7.3.3; fixed BUILD SUCCESSFUL and buggy trigger failed |
| SWIFT-D009 | PASS | FIX9_DIRECT_DYNAMIC | summary.passed=true and both runner outputs report expected_outcome_observed=true |
| SWIFT-D048 | PASS | FIX9_REPORT_AND_VERIFY_RC | verify rc=0 is present; remote run log records both fixed and buggy runner_exit_code=0; no standalone summary.json is bundled |
| SWIFT-D049 | PASS | FIX9_DIRECT_DYNAMIC | remote summary.passed=true, both runner outputs report expected_outcome_observed=true, and verify D049 rc=0; fixed full-suite evidence reaches 381/381 with DumpHelpGenerationTests skipped |
| ELIXIR-026 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-054 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-081 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-093 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-098 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-099 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| ELIXIR-100 | PASS | BLOCKER_REPAIR_DIRECT_DYNAMIC | offline dependency closure and buggy/fixed trigger acceptance completed in the 7-case replay |
| KOTLIN-501 | PASS | STRICT_FULL_SUITE_PASS_PDF_RETRY_SHIM | Node/npm dependency closure PASS; trigger contract 3/3 buggy and 3/3 fixed; fixed full suite passed 3/3; PDF readiness retry shim applied symmetrically in the disposable replay runner |

Repair overlay counts: `{'PASS': 17}`。其中 fix9 为 9 个案例，blocker-repair 为 8 个此前阻塞案例。

## 与原全量账本的合并结果

After blocker repair, the uncapped active count was {'PASS': 855}; after the R=100 cap and SWIFT-D101 addendum, the release active count is {'PASS': 850}.

SWIFT-D051 remains excluded; the R=100 cap removes six R records. SWIFT-D101 brings the release active count to 850.

## 按语言

| language | PASS | PARTIAL | FAIL | BLOCKED |
|---|---:|---:|---:|---:|
| arkts | 50 | 0 | 0 | 0 |
| dart | 100 | 0 | 0 | 0 |
| elixir | 100 | 0 | 0 | 0 |
| julia | 100 | 0 | 0 | 0 |
| kotlin | 100 | 0 | 0 | 0 |
| lua | 100 | 0 | 0 | 0 |
| perl | 100 | 0 | 0 | 0 |
| r | 100 | 0 | 0 | 0 |
| swift | 100 | 0 | 0 | 0 |

## 发布材料问题

- `delivery/packages/SHA256SUMS.txt` 使用远程绝对路径；已在同一目录旁生成 `delivery/packages/SHA256SUMS.relative.txt`，可直接在该目录执行 `sha256sum -c SHA256SUMS.relative.txt`。
- Swift-D048 缺少独立 `summary.json`；当前只有 `verify SWIFT-D048 rc=0` 行。
- Swift-D049 的 ZIP 外层日志不完整；已从 ygd 远端取回 `swift-work2/SWIFT-D049/summary.json` 与 `verify D049 rc=0` 证据，因此在本叠加层按 PASS 记录。
- Swift 包内目录 ID 与部分 `case.json.case_id` 不一致，见 `fix9-evidence.json` 的 `metadata_issues`。

## 输出

- `fix9-audit-20261014/fix9-evidence.json`：逐案证据解析、包哈希和问题清单。
- `fix9-audit-20261014/final-case-ledger-fix9-overlay.jsonl`：原账本的 fix9 overlay。
- `fix9-audit-20261014/final-summary-fix9-overlay.json`：合并计数。
- `SHA256SUMS.packages.relative.txt`：可重定位的三包校验清单。

## R=100 移除记录

- VCTRS-8
- VCTRS-9
- VCTRS-10
- VCTRS-11
- WALDO-1
- WITHR-1
