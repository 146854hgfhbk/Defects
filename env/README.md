# Environment matrix

Defects4X is deliberately **per-case pinned**. Do not assume one global version per language.

| Language | Cases | Recommended mode | Versions observed |
|---|---:|---|---|
| Dart | 100 | native SDK | 2.0.0, 2.5.2, 2.7.2, 2.9.3, 2.10.5, 2.12.4, 2.13.4, 2.14.4, 2.18.6, 2.19.6, 3.5.4, 3.10.0, 3.12.2 |
| Julia | 100 | native Julia | 1.6.7, 1.8.5, 1.9.1, 1.10.12, 1.12.7 |
| Kotlin | 100 | native JDK + Gradle | JDK 17/21/25; Gradle 7.2–9.5; Kotlin 2.1–2.4 |
| Lua | 100 | native Lua + LuaRocks | Lua 5.4.8, LuaRocks 3.11.1, Busted 2.2.0-1 |
| Perl | 100 | native Perl or container | Perl 5.24 / 5.36 |
| R | 100 | native R | R 4.4.3 |
| Elixir | 100 | container / native OTP | per-case image; OTP 26 / Elixir 1.16.3 |
| Swift | 100 | container / Swift toolchain | Swift 5.10.1, 6.1, 6.2.3 |
| ArkTS | 50 | device | SDK + authorized device + signing |

Per-case table: [case-matrix.tsv](case-matrix.tsv).

The authoritative version for a case is:

```bash
cat cases/<language>/<CASE_ID>/environment.lock.json
cat cases/<language>/<CASE_ID>/environment.json
```

If these disagree with the language guide, **the case lock wins**.

## Base OS

All Linux reference evidence was produced on:

```text
Ubuntu 26.04 LTS, x86_64, glibc 2.43, UTC, en-US, UTF-8
```

Other distributions may work, but old SDKs and native extensions are the main source of drift. Use a clean VM/container per language.

## Network

Most cases declare `network: none` or `network_isolation: os_enforced`. Prepare dependencies **before** the run, then disable network:

```bash
unshare -n -- bash -lc '<replay command>'
```

If the case is not declared offline, network is allowed but must be recorded.
