#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PREFIX="$TMP/termux"
HOME="$TMP/home"
TARGET="$HOME/Psion-sidecar-test"
BACKUPS="$HOME/backups"
FIXTURE="$TMP/fixture"
ARCHIVE="$TMP/source.tar.gz"
MOCK_BIN="$TMP/mock-bin"
SERVICE="psion-sidecar-test"
PORT="8082"
COMMIT="0123456789abcdef0123456789abcdef01234567"

mkdir -p "$PREFIX/bin" "$PREFIX/var/service/$SERVICE"
mkdir -p "$HOME" "$FIXTURE/Sidecar-main" "$MOCK_BIN"
mkdir -p "$TARGET/crosswords"

# Mock Termux Python for isolated updater tests; no Mac Python required.
cat > "$PREFIX/bin/python" <<'MOCKPY'
#!/bin/sh
[ "$1" = "-m" ] && [ "$2" = "py_compile" ] || exit 2
shift 2
for file in "$@"; do
    [ -f "$file" ] || exit 1
done
exit 0
MOCKPY
chmod +x "$PREFIX/bin/python"

# Mock GitHub commit lookup; reject incorrect repository or branch.
cat > "$MOCK_BIN/git" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$TEST_GIT_LOG"

[ "$#" -eq 3 ] || exit 1
[ "$1" = "ls-remote" ] || exit 1
[ "$2" = "$TEST_REPOSITORY" ] || exit 1
[ "$3" = "refs/heads/main" ] || exit 1

printf '%s\trefs/heads/main\n' "$TEST_COMMIT"
MOCK

# Mock archive download and HTTP health check.
cat > "$MOCK_BIN/curl" <<'MOCK'
#!/bin/sh
set -eu

last=""
output=""
previous=""
write_format=""

for arg in "$@"; do
    last="$arg"
    if [ "$previous" = "-o" ]; then
        output="$arg"
    fi
    if [ "$previous" = "-w" ]; then
        write_format="$arg"
    fi
    previous="$arg"
done

if [ "$last" = "$TEST_ARCHIVE_URL" ]; then
    case "$output" in
        */source.tar.gz) ;;
        *)
            echo "MOCK ERROR: incorrect archive destination: $output" >&2
            exit 1
            ;;
    esac

    printf '%s\n' "$last" >> "$TEST_CURL_ARCHIVE_LOG"
    printf '%s\n' "$output" >> "$TEST_CURL_DEST_LOG"
    /bin/cp "$TEST_ARCHIVE" "$output"
    exit 0
fi

[ "$last" = "$TEST_HEALTH_URL" ] || {
    echo "MOCK ERROR: incorrect health-check URL: $last" >&2
    exit 1
}

[ "$output" = "/dev/null" ] || {
    echo "MOCK ERROR: incorrect health-check output destination: $output" >&2
    exit 1
}

[ "$write_format" = "%{http_code}" ] || {
    echo "MOCK ERROR: missing HTTP status format" >&2
    exit 1
}

if [ -f "$TEST_HEALTH_FAIL" ]; then
    printf '000'
    exit 22
fi

printf '200'
exit 0
MOCK

# Mock runit commands and record exactly which service is affected.
cat > "$MOCK_BIN/sv" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' "$*" >> "$TEST_SV_LOG"

case "$1" in
    status|down|up) exit 0 ;;
    *) exit 1 ;;
esac
MOCK

# Mock sleep so health-check retries run immediately.
cat > "$MOCK_BIN/sleep" <<'MOCK'
#!/bin/sh
exit 0
MOCK

# Allow a controlled failure while installing staged application files.
cat > "$MOCK_BIN/cp" <<'MOCK'
#!/bin/sh
set -eu

previous=""
last=""
for arg in "$@"; do
    previous="$last"
    last="$arg"
done

case "$last" in
    "$TEST_BACKUPS"/backup-*/*)
        if [ -f "$TEST_BACKUP_CORRUPT" ]; then
            /bin/cp "$@"
            printf "deliberate corruption" >> "$last"
            exit 0
        fi
        ;;
esac

case "$last" in
    "$TEST_TARGET"/*)
        case "$previous" in
            *"/stage/"*)
                if [ -f "$TEST_INSTALL_FAIL" ]; then
                    rm -f "$TEST_INSTALL_FAIL"
                    echo "MOCK: simulated staged-file installation failure" >&2
                    exit 1
                fi
                ;;
        esac
        ;;
esac

exec /bin/cp "$@"
MOCK

chmod +x "$MOCK_BIN/"*

export PREFIX HOME PATH="$MOCK_BIN:$PATH"
export TEST_COMMIT="$COMMIT"
export TEST_REPOSITORY="https://github.com/Shredder61/Psion-sidecar.git"
export TEST_ARCHIVE_URL="https://codeload.github.com/Shredder61/Psion-sidecar/tar.gz/$COMMIT"
export TEST_HEALTH_URL="http://127.0.0.1:$PORT/"
export TEST_GIT_LOG="$TMP/git.log"
export TEST_CURL_ARCHIVE_LOG="$TMP/curl-archive.log"
export TEST_CURL_DEST_LOG="$TMP/curl-destination.log"
export TEST_ARCHIVE="$ARCHIVE"
export TEST_TARGET="$TARGET"
export TEST_HEALTH_FAIL="$TMP/health-fail"
export TEST_INSTALL_FAIL="$TMP/install-fail"
export TEST_SV_LOG="$TMP/sv.log"
export TEST_BACKUPS="$BACKUPS"
export TEST_BACKUP_CORRUPT="$TMP/backup-corrupt"

# Build a GitHub-style source archive with six application files.
write_fixture() {
    version="$1"
    for file in \
        sidecar_web.py \
        guardian_pi.py \
        crossword_converter.py
    do
        printf 'VERSION = "%s"\n' "$version" \
            > "$FIXTURE/Sidecar-main/$file"
    done

    for file in software_index.json epoc16_index.json epoc32_index.json; do
        printf '{"version":"%s"}\n' "$version" \
            > "$FIXTURE/Sidecar-main/$file"
    done

    tar -czf "$ARCHIVE" -C "$FIXTURE" Sidecar-main
}

write_run_file() {
    cat > "$PREFIX/var/service/$SERVICE/run" <<RUN
#!/bin/sh
cd "$TARGET" || exit 1
exec "$PREFIX/bin/python" "$TARGET/sidecar_web.py" --port $PORT
RUN
}

seed_old_install() {
    for file in \
        sidecar_web.py guardian_pi.py crossword_converter.py \
        software_index.json epoc16_index.json epoc32_index.json
    do
        printf 'VERSION = "old"\n' > "$TARGET/$file"
    done
}

run_updater() {
    sh "$ROOT/scripts/update-termux-sidecar" \
        --target "$TARGET" \
        --service "$SERVICE" \
        --port "$PORT" \
        --backup-dir "$BACKUPS"
}

write_fixture "new"
write_run_file
seed_old_install
printf 'keep this crossword\n' > "$TARGET/crosswords/keep.txt"

echo "=== Test 1: successful update ==="
run_updater > "$TMP/success.log"
grep -q 'SUCCESS: Termux Sidecar updated and responding.' "$TMP/success.log"
grep -q 'VERSION = "new"' "$TARGET/sidecar_web.py"
grep -q '"version":"new"' "$TARGET/software_index.json"
grep -q 'keep this crossword' "$TARGET/crosswords/keep.txt"
grep -Fxq "ls-remote $TEST_REPOSITORY refs/heads/main" "$TEST_GIT_LOG"
grep -Fxq "$TEST_ARCHIVE_URL" "$TEST_CURL_ARCHIVE_LOG"
grep -Eq "/source[.]tar[.]gz$" "$TEST_CURL_DEST_LOG"
grep -q '^down '"$SERVICE"'$' "$TEST_SV_LOG"
grep -q '^up '"$SERVICE"'$' "$TEST_SV_LOG"
test -n "$(find "$BACKUPS" -name source-commit -print -quit)"
echo "PASS: update, backup, service selection and crossword preservation"

echo
echo "=== Test 2: installation failure rolls back ==="
seed_old_install
: > "$TEST_INSTALL_FAIL"
: > "$TEST_SV_LOG"
if run_updater > "$TMP/install-failure.log" 2>&1; then
    echo "FAIL: installation failure was not detected"
    exit 1
else
    echo "Updater returned expected failure status."
    cat "$TMP/install-failure.log"
fi
grep -q 'VERSION = "old"' "$TARGET/sidecar_web.py"
grep -q 'UPDATE FAILED. Attempting to restore the previous application.' "$TMP/install-failure.log"
grep -q '^up '"$SERVICE"'$' "$TEST_SV_LOG"
echo "PASS: installation failure restores old files and restarts selected service"

echo
echo "=== Test 3: health-check failure rolls back ==="
seed_old_install
: > "$TEST_HEALTH_FAIL"
: > "$TEST_SV_LOG"
if run_updater > "$TMP/health-failure.log" 2>&1; then
    echo "FAIL: health-check failure was not detected"
    exit 1
else
    echo "Updater returned expected health-check failure status."
    cat "$TMP/health-failure.log"
fi
rm -f "$TEST_HEALTH_FAIL"
grep -q 'VERSION = "old"' "$TARGET/sidecar_web.py"
grep -q 'UPDATE FAILED. Attempting to restore the previous application.' "$TMP/health-failure.log"
grep -q '^up '"$SERVICE"'$' "$TEST_SV_LOG"
echo "PASS: health-check failure restores old files and restarts selected service"

echo
echo "=== Test 4: wrong port is rejected before update ==="
seed_old_install
: > "$TEST_SV_LOG"
if sh "$ROOT/scripts/update-termux-sidecar" \
    --target "$TARGET" --service "$SERVICE" --port 8081 \
    --backup-dir "$BACKUPS" > "$TMP/wrong-port.log" 2>&1
then
    echo "FAIL: mismatched service port was accepted"
    exit 1
fi
grep -q 'does not specify the selected port' "$TMP/wrong-port.log"
grep -q 'VERSION = "old"' "$TARGET/sidecar_web.py"
test ! -s "$TEST_SV_LOG"
echo "PASS: mismatched port rejected without stopping the service"

echo
echo

echo "=== Test 5: corrupted backup is rejected before service stop ==="

seed_old_install
: > "$TEST_SV_LOG"
: > "$TEST_BACKUP_CORRUPT"

if run_updater > "$TMP/backup-corruption.log" 2>&1; then
    echo "FAIL: corrupted backup was accepted"
    exit 1
fi

rm -f "$TEST_BACKUP_CORRUPT"

grep -q 'Backup verification failed:' "$TMP/backup-corruption.log"
grep -q 'VERSION = "old"' "$TARGET/sidecar_web.py"
grep -q '^status '"$SERVICE"'$' "$TEST_SV_LOG"

if grep -q '^down '"$SERVICE"'$' "$TEST_SV_LOG"; then
    echo "FAIL: service was stopped despite corrupted backup"
    exit 1
fi

if grep -q '^up '"$SERVICE"'$' "$TEST_SV_LOG"; then
    echo "FAIL: service was restarted despite corrupted backup"
    exit 1
fi

echo "PASS: corrupted backup rejected; original files and running service left untouched"

echo

echo "All Termux updater tests passed."
