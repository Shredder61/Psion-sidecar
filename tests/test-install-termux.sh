#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PREFIX="$TMP/termux"
HOME="$TMP/home"
TARGET="$HOME/Psion-sidecar-test"

mkdir -p "$PREFIX/bin" "$PREFIX/var/service" "$HOME"

# Simulated Termux Python executable.
cat > "$PREFIX/bin/python" <<'MOCK'
#!/bin/sh
exit 0
MOCK
chmod +x "$PREFIX/bin/python"

# Test 1: install into isolated test directory.
export PREFIX HOME
sh "$ROOT/scripts/install-termux.sh" --target "$TARGET"

for file in \
    sidecar_web.py \
    guardian_pi.py \
    crossword_converter.py \
    software_index.json \
    epoc16_index.json \
    epoc32_index.json
do
    test -f "$TARGET/$file"
done

echo "PASS: application files installed"

# Test 2: existing crossword data is preserved.
printf 'test crossword\n' > "$TARGET/crosswords/test.txt"

sh "$ROOT/scripts/install-termux.sh" --target "$TARGET"

test -f "$TARGET/crosswords/test.txt"
echo "PASS: existing crossword data preserved"

# Test 3: no service is created without --enable.
test ! -e "$PREFIX/var/service/psion-sidecar"
echo "PASS: service untouched without --enable"

# Test 4: existing service is protected.
mkdir -p "$PREFIX/var/service/psion-sidecar"
printf 'existing service\n' > "$PREFIX/var/service/psion-sidecar/run"

if sh "$ROOT/scripts/install-termux.sh" \
    --target "$TARGET" --enable
then
    echo "FAIL: existing service was not rejected"
    exit 1
fi

grep -q 'existing service' "$PREFIX/var/service/psion-sidecar/run"
echo "PASS: existing service protected"


# Test 5: simulate failure during application-file replacement.
FILES="
sidecar_web.py
guardian_pi.py
crossword_converter.py
software_index.json
epoc16_index.json
epoc32_index.json
"

for file in $FILES; do
    printf 'ORIGINAL-%s\n' "$file" > "$TARGET/$file"
done

MOCK_BIN="$TMP/mock-bin"
mkdir -p "$MOCK_BIN"

cat > "$MOCK_BIN/cp" <<'MOCK'
#!/bin/sh
set -eu

case "$*" in
    *"/stage/"*)
        count=0
        [ ! -f "$TEST_CP_COUNT" ] || count="$(cat "$TEST_CP_COUNT")"
        count=$((count + 1))
        printf '%s\n' "$count" > "$TEST_CP_COUNT"

        if [ "$count" -eq 2 ] && [ ! -f "$TEST_CP_FAILED" ]; then
            : > "$TEST_CP_FAILED"
            exit 1
        fi
        ;;
esac

exec /bin/cp "$@"
MOCK

chmod +x "$MOCK_BIN/cp"

export TEST_CP_COUNT="$TMP/cp-count"
export TEST_CP_FAILED="$TMP/cp-failed"
export PATH="$MOCK_BIN:$PATH"

if sh "$ROOT/scripts/install-termux.sh" --target "$TARGET"; then
    echo "FAIL: simulated installation failure was not detected"
    exit 1
fi

for file in $FILES; do
    grep -qx "ORIGINAL-$file" "$TARGET/$file"
done

echo "PASS: all original application files restored after failure"
echo "All Termux installer tests passed."
