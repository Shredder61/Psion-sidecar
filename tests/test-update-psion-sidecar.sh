#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
chmod 0755 "$TMP"
MOCK_BIN="$TMP/mock-bin"
SEED="$TMP/seed"
BARE="$TMP/origin.git"
REPO="$TMP/Psion-sidecar"
APP="$TMP/installed"
BACKUPS="$TMP/backups"
mkdir -p "$MOCK_BIN" "$SEED" "$APP/crosswords" "$BACKUPS"
trap 'rm -rf "$TMP"' EXIT

if ! id sidecar >/dev/null 2>&1; then
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin sidecar
fi

cat > "$MOCK_BIN/systemctl" <<'MOCK'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "${TEST_SYSTEMCTL_LOG:?}"
case "$1" in
  is-active) exit 0 ;;
  stop|start|daemon-reload) exit 0 ;;
  *) exit 0 ;;
esac
MOCK

cat > "$MOCK_BIN/install" <<'MOCK'
#!/usr/bin/env bash
set -eu
last="${!#}"
if [[ -f "${TEST_INSTALL_FAIL_FILE:?}" && "$last" == */guardian_pi.py ]]; then
    rm -f "$TEST_INSTALL_FAIL_FILE"
    exit 1
fi
exec /usr/bin/install "$@"
MOCK

cat > "$MOCK_BIN/curl" <<'MOCK'
#!/usr/bin/env bash
if [[ -f "${TEST_CURL_FAIL_FILE:?}" ]]; then
    exit 22
fi
exit 0
MOCK

cat > "$MOCK_BIN/sleep" <<'MOCK'
#!/usr/bin/env bash
exit 0
MOCK
chmod +x "$MOCK_BIN/"*

git init --bare --initial-branch=main "$BARE" >/dev/null
git init --initial-branch=main "$SEED" >/dev/null
git -C "$SEED" config user.name "Updater Test"
git -C "$SEED" config user.email "updater-test@example.invalid"

write_fixture() {
    local version="$1"
    printf 'VERSION = "%s"\n' "$version" > "$SEED/sidecar_web.py"
    printf 'VERSION = "%s"\n' "$version" > "$SEED/guardian_pi.py"
    printf 'VERSION = "%s"\n' "$version" > "$SEED/crossword_converter.py"
    printf '{"version":"%s"}\n' "$version" > "$SEED/epoc16_index.json"
    printf '{"version":"%s"}\n' "$version" > "$SEED/epoc32_index.json"
    printf '{"version":"%s"}\n' "$version" > "$SEED/software_index.json"
}

write_fixture "v1"
git -C "$SEED" add .
git -C "$SEED" commit -m "fixture v1" >/dev/null
git -C "$SEED" remote add origin "$BARE"
git -C "$SEED" push -u origin main >/dev/null
git clone "$BARE" "$REPO" >/dev/null 2>&1
OLD_CHECKOUT="$(git -C "$REPO" rev-parse HEAD)"

# Publish a newer upstream commit after the local checkout was cloned.
write_fixture "v2"
git -C "$SEED" add .
git -C "$SEED" commit -m "fixture v2" >/dev/null
git -C "$SEED" push origin main >/dev/null

# Seed the installed app with the old version. Keep crosswords writable by
# the service account; other application files are root-owned.
for file in sidecar_web.py guardian_pi.py crossword_converter.py epoc16_index.json epoc32_index.json software_index.json; do
    printf 'VERSION = "old"\n' > "$APP/$file"
done
sudo chown root:root "$APP"
sudo chown sidecar:sidecar "$APP/crosswords"
sudo chmod 0755 "$APP" "$APP/crosswords"

# Use a temporary copy with paths redirected into this test directory.
TEST_UPDATER="$TMP/update-psion-sidecar"
CURRENT_USER="$(id -un)"
sed \
  -e "s|^REPO=\"/home/pi/Psion-sidecar\"|REPO=\"$REPO\"|" \
  -e "s|^APP=\"/opt/psion-sidecar\"|APP=\"$APP\"|" \
  -e "s|^BACKUP_DIR=\"/var/backups/psion-sidecar\"|BACKUP_DIR=\"$BACKUPS\"|" \
  -e "s|^REPO_USER=\"pi\"|REPO_USER=\"$CURRENT_USER\"|" \
  "$ROOT_DIR/scripts/update-psion-sidecar" > "$TEST_UPDATER"
chmod 0755 "$TEST_UPDATER"

export TEST_SYSTEMCTL_LOG="$TMP/systemctl.log"
export TEST_CURL_FAIL_FILE="$TMP/curl-fail"
export TEST_INSTALL_FAIL_FILE="$TMP/install-fail"
export PATH="$MOCK_BIN:$PATH"

# Success case: install v2 from fetched origin/main without advancing HEAD.
# shellcheck disable=SC2024 # Redirect into the unprivileged test harness temp directory.
sudo env PATH="$PATH" TEST_SYSTEMCTL_LOG="$TEST_SYSTEMCTL_LOG" TEST_CURL_FAIL_FILE="$TEST_CURL_FAIL_FILE" TEST_INSTALL_FAIL_FILE="$TEST_INSTALL_FAIL_FILE" bash "$TEST_UPDATER" > "$TMP/success.log"
grep -q 'SUCCESS: Sidecar updated and responding.' "$TMP/success.log"
grep -q 'VERSION = "v2"' "$APP/sidecar_web.py"
test "$(git -C "$REPO" rev-parse HEAD)" = "$OLD_CHECKOUT"
grep -q 'Local checkout left unchanged.' "$TMP/success.log"
echo "PASS: successful update installs fetched version without moving local checkout"

# Failure case 1: fail an application-file install to exercise the ERR trap.
for file in sidecar_web.py guardian_pi.py crossword_converter.py epoc16_index.json epoc32_index.json software_index.json; do
    printf 'VERSION = "old"\\n' > "$APP/$file"
done
sudo chown root:root "$APP/"*
touch "$TEST_INSTALL_FAIL_FILE"
set +e
# shellcheck disable=SC2024 # Redirect into the unprivileged test harness temp directory.
sudo env PATH="$PATH" TEST_SYSTEMCTL_LOG="$TEST_SYSTEMCTL_LOG" TEST_CURL_FAIL_FILE="$TEST_CURL_FAIL_FILE" TEST_INSTALL_FAIL_FILE="$TEST_INSTALL_FAIL_FILE" bash "$TEST_UPDATER" > "$TMP/install-failure.log" 2>&1
status=$?
set -e
test "$status" -ne 0
grep -q 'UPDATE FAILED. Restoring the previous application files' "$TMP/install-failure.log"
grep -q 'VERSION = "old"' "$APP/sidecar_web.py"
grep -q '^start psion-sidecar.servicefor file in sidecar_web.py guardian_pi.py crossword_converter.py epoc16_index.json epoc32_index.json software_index.json; do
    printf 'VERSION = "old"\n' > "$APP/$file"
done
sudo chown root:root "$APP/"*
touch "$TEST_CURL_FAIL_FILE"
set +e
# shellcheck disable=SC2024 # Redirect into the unprivileged test harness temp directory.
sudo env PATH="$PATH" TEST_SYSTEMCTL_LOG="$TEST_SYSTEMCTL_LOG" TEST_CURL_FAIL_FILE="$TEST_CURL_FAIL_FILE" TEST_INSTALL_FAIL_FILE="$TEST_INSTALL_FAIL_FILE" bash "$TEST_UPDATER" > "$TMP/failure.log" 2>&1
status=$?
set -e
rm -f "$TEST_CURL_FAIL_FILE"
test "$status" -ne 0
grep -q 'UPDATE FAILED. Restoring the previous application files' "$TMP/failure.log"
grep -q 'VERSION = "old"' "$APP/sidecar_web.py"
grep -q '^start psion-sidecar.service$' "$TEST_SYSTEMCTL_LOG"
echo "PASS: simulated health-check failure restores previous files and attempts service restart"

echo "All isolated updater tests passed."
 "$TEST_SYSTEMCTL_LOG"
echo "PASS: install-command failure triggers ERR-trap rollback"

# Failure case 2: simulate a health-check failure and verify explicit rollback.
for file in sidecar_web.py guardian_pi.py crossword_converter.py epoc16_index.json epoc32_index.json software_index.json; do
    printf 'VERSION = "old"\n' > "$APP/$file"
done
sudo chown root:root "$APP/"*
touch "$TEST_CURL_FAIL_FILE"
set +e
sudo env PATH="$PATH" TEST_SYSTEMCTL_LOG="$TEST_SYSTEMCTL_LOG" TEST_CURL_FAIL_FILE="$TEST_CURL_FAIL_FILE" bash "$TEST_UPDATER" > "$TMP/failure.log" 2>&1
status=$?
set -e
rm -f "$TEST_CURL_FAIL_FILE"
test "$status" -ne 0
grep -q 'UPDATE FAILED. Restoring the previous application files' "$TMP/failure.log"
grep -q 'VERSION = "old"' "$APP/sidecar_web.py"
grep -q '^start psion-sidecar.service$' "$TEST_SYSTEMCTL_LOG"
echo "PASS: simulated health-check failure restores previous files and attempts service restart"

echo "All isolated updater tests passed."
