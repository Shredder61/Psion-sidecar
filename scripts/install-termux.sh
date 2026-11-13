#!/data/data/com.termux/files/usr/bin/sh

set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"
TARGET="$HOME/Psion-sidecar"

FILES="
sidecar_web.py
guardian_pi.py
crossword_converter.py
software_index.json
epoc16_index.json
epoc32_index.json
"

usage() {
    echo "Usage: $0 [--target DIRECTORY]"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --target)
            [ "$#" -ge 2 ] || {
                echo "ERROR: --target requires a directory"
                exit 2
            }
            TARGET="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            usage
            exit 2
            ;;
    esac
done

case "$TARGET" in
    /*) ;;
    *)
        echo "ERROR: Target must be an absolute path"
        exit 2
        ;;
esac

if [ -z "${PREFIX:-}" ] || [ ! -x "$PREFIX/bin/python" ]; then
    echo "ERROR: Run inside Termux with Python installed."
    exit 1
fi

for file in $FILES; do
    [ -f "$SOURCE_DIR/$file" ] || {
        echo "ERROR: Required source file missing: $SOURCE_DIR/$file"
        exit 1
    }
done

mkdir -p "$TARGET/crosswords"

WORK="$(mktemp -d "$TARGET/.sidecar-install.XXXXXX")"
STAGE="$WORK/stage"
BACKUP="$WORK/backup"

CHANGED=0
SUCCESS=0

mkdir -p "$STAGE" "$BACKUP"

cleanup() {
    if [ "$SUCCESS" -ne 1 ] && [ "$CHANGED" -eq 1 ]; then
        echo "Installation failed: restoring previous application files."
        for file in $FILES; do
            if [ -f "$BACKUP/$file" ]; then
                cp -p "$BACKUP/$file" "$TARGET/$file" || true
            else
                rm -f "$TARGET/$file"
            fi
        done
    fi
    rm -rf "$WORK"
}

trap cleanup EXIT HUP INT TERM

echo "Staging application files..."

for file in $FILES; do
    cp "$SOURCE_DIR/$file" "$STAGE/$file"
done

echo "Checking Python syntax..."

for file in sidecar_web.py guardian_pi.py crossword_converter.py; do
    "$PREFIX/bin/python" -m py_compile "$STAGE/$file"
done

rm -rf "$STAGE/__pycache__"

echo "Backing up existing application files..."

for file in $FILES; do
    if [ -f "$TARGET/$file" ]; then
        cp -p "$TARGET/$file" "$BACKUP/$file"
    fi
done

echo "Installing validated files..."

CHANGED=1

for file in $FILES; do
    cp "$STAGE/$file" "$TARGET/$file"
done

SUCCESS=1

echo "Installation completed successfully."
echo "Existing crossword data and services were left untouched."
