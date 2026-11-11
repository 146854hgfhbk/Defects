#!/usr/bin/env bash
# Prepare the exact Gradle wrapper distribution for KOTLIN-100.
# Usage: GRADLE_USER_HOME=/path/to/gradle-home ./scripts/prepare_kotlin100_gradle.sh [archive-or-url]
# The optional source defaults to Gradle's official URL. A mirror or local file is
# accepted only when its bytes match the official SHA-256 pinned below.
set -euo pipefail

: "${GRADLE_USER_HOME:?Set GRADLE_USER_HOME to the Gradle cache directory to prepare}"
source_arg=${1:-https://services.gradle.org/distributions/gradle-8.14.3-bin.zip}
expected_sha256=bd71102213493060956ec229d946beee57158dbd89d0e62b91bca0fa2c5f3531
dist_name=gradle-8.14.3-bin
dist_hash=cv11ve7ro1n3o1j4so8xd9n66
archive_name=${dist_name}.zip
base_dir=$GRADLE_USER_HOME/wrapper/dists/$dist_name
entry_dir=$base_dir/$dist_hash

mkdir -p "$base_dir" "$GRADLE_USER_HOME/caches/8.14.3"
# Gradle Wrapper uses a Java FileChannel lock on the .lck file. Hold that same
# lock for the whole preparation so a wrapper cannot download into this entry.
mkdir -p "$entry_dir"
lock_file=$entry_dir/$archive_name.lck
export lock_file
python3 - "$lock_file" <<'PYLOCK' &
import fcntl, os, sys, time
with open(sys.argv[1], "a+b") as lock:
    try:
        fcntl.lockf(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit(1)
    print("locked", flush=True)
    while True:
        time.sleep(3600)
PYLOCK
lock_pid=$!
# Wait until the helper either holds the lock or exits. /proc avoids relying on
# shell job-control state; this helper is Linux-specific like this environment.
for _ in 1 2 3 4 5; do
  if ! kill -0 "$lock_pid" 2>/dev/null; then
    wait "$lock_pid" || true
    echo "The wrapper entry is in use: $entry_dir" >&2
    exit 1
  fi
  if grep -q "POSIX.*$lock_pid" /proc/locks; then break; fi
  sleep 1
done
if ! grep -q "POSIX.*$lock_pid" /proc/locks; then
  kill "$lock_pid" 2>/dev/null || true
  echo "Could not confirm wrapper lock: $entry_dir" >&2
  exit 1
fi
cleanup_lock() { kill "$lock_pid" 2>/dev/null || true; wait "$lock_pid" 2>/dev/null || true; }
trap cleanup_lock EXIT
if [ -e "$entry_dir/$archive_name.ok" ] || [ -e "$entry_dir/gradle-8.14.3" ] || [ -e "$entry_dir/$archive_name.part" ]; then
  echo "Refusing to replace an existing or partial wrapper entry: $entry_dir" >&2
  echo "Use a fresh GRADLE_USER_HOME, or verify and reuse the existing entry." >&2
  exit 1
fi
tmp_dir=$(mktemp -d "$base_dir/.prepare-kotlin100.XXXXXX")
trap 'rm -rf "$tmp_dir"; cleanup_lock' EXIT
archive=$tmp_dir/$archive_name
if [ -f "$source_arg" ]; then
  cp -- "$source_arg" "$archive"
else
  curl -fL --retry 3 --connect-timeout 20 -o "$archive" "$source_arg"
fi
printf '%s  %s\n' "$expected_sha256" "$archive" | sha256sum -c -
python3 - "$archive" "$tmp_dir" <<'PY'
import sys, zipfile
from pathlib import Path

archive = Path(sys.argv[1])
destination = Path(sys.argv[2]).resolve()
with zipfile.ZipFile(archive) as data:
    for member in data.infolist():
        target = (destination / member.filename).resolve()
        if not target.is_relative_to(destination):
            raise SystemExit(f"Unsafe archive member: {member.filename}")
    data.extractall(destination)
    for member in data.infolist():
        mode = (member.external_attr >> 16) & 0o777
        target = destination / member.filename
        if mode and target.exists():
            target.chmod(mode)
PY
test -x "$tmp_dir/gradle-8.14.3/bin/gradle"
mv "$tmp_dir/gradle-8.14.3" "$entry_dir/gradle-8.14.3"
mv "$archive" "$entry_dir/$archive_name"
# The marker is published last while the wrapper lock is held.
touch "$entry_dir/$archive_name.ok"
printf 'Prepared %s\nSHA-256: %s\n' "$entry_dir" "$expected_sha256"
printf 'Set GRADLE_USER_HOME=%s when running d4x.\n' "$GRADLE_USER_HOME"
