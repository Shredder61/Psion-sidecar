
# Install Psion Sidecar on Android using Termux

These instructions describe running Psion Sidecar on an Android device using Termux and `termux-services` (runit). They are separate from the Raspberry Pi and systemd installation described in [INSTALL.md](INSTALL.md).

The examples use:

| Purpose | Application directory | Service | HTTP port |
|---|---|---|---:|
| Main Sidecar | `~/Psion-sidecar` | `psion-sidecar` | 8081 |
| Optional test instance | `~/Psion-sidecar-test` | `psion-sidecar-test` | 8082 |

The two instances have separate application files, services and ports. Updating one does not require stopping or changing the other.

## 1. Prepare Termux

Open Termux on the Android device and install the required packages:

```sh
pkg update
pkg install git python curl tar termux-services
```

After installing `termux-services`, close and reopen the Termux shell so its service daemon starts.

The application uses Python's standard library and does not require third-party Python packages.

## 2. Obtain the repository

Clone the repository into a source directory separate from the installed application:

```sh
git clone https://github.com/Shredder61/Psion-sidecar.git "$HOME/Psion-sidecar-source"
cd "$HOME/Psion-sidecar-source"
```

Keep this source checkout separate from `~/Psion-sidecar`. The installer copies application files from the repository into the selected installation directory.

## 3. Install the main application

From the repository directory, run:

```sh
./scripts/install-termux.sh --target "$HOME/Psion-sidecar"
```

The installer checks that it is running inside Termux, verifies the required source files, checks Python syntax, backs up existing application files temporarily, and installs the validated files.

The installer's temporary backup is removed after successful installation. If installation fails after copying begins, the installer attempts to restore the previous application files. This temporary backup is separate from the persistent backups created by the updater.

It creates the `crosswords` directory if necessary. Existing crossword data and runit services are left untouched. The installer does not create, enable, stop or modify a service.

The installed application includes:

- `sidecar_web.py`
- `guardian_pi.py`
- `crossword_converter.py`
- `software_index.json`
- `epoc16_index.json`
- `epoc32_index.json`

All three catalogue index files must be present beside `sidecar_web.py` for the software catalogue to work fully.

## 4. Configure the main runit service

The repository includes a runit service template:

`termux/services/psion-sidecar/run`

This template starts Sidecar from `~/Psion-sidecar` on port 8081. Install it into Termux's service directory.

Create the service and logging directories:

```sh
mkdir -p "$PREFIX/var/service/psion-sidecar/log"
```

Copy the supplied run file into place:

```sh
cp "$HOME/Psion-sidecar-source/termux/services/psion-sidecar/run" \
   "$PREFIX/var/service/psion-sidecar/run"
```

Make the run file executable:

```sh
chmod +x "$PREFIX/var/service/psion-sidecar/run"
```

Configure the service logger:

```sh
ln -sf "$PREFIX/share/termux-services/svlogger" \
   "$PREFIX/var/service/psion-sidecar/log/run"
```

Check that the installed run file refers to the correct application path and port:

```sh
cat "$PREFIX/var/service/psion-sidecar/run"
```

It should start:

`$HOME/Psion-sidecar/sidecar_web.py`

with:

`--port 8081`

Enable and start the service:

```sh
sv-enable psion-sidecar
```

Check its status:

```sh
sv status psion-sidecar
```

Check the local HTTP response:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8081/
```

A successful response should normally report HTTP status `200`.

Service output is recorded in:

`$PREFIX/var/log/sv/psion-sidecar/current`

To inspect recent log entries:

```sh
tail -n 30 "$PREFIX/var/log/sv/psion-sidecar/current"
```

To stop or restart the service:

```sh
sv down psion-sidecar
sv up psion-sidecar
```

The service definition must explicitly reference the installed application path and port. The Sidecar updater checks these details before attempting an update.

## 5. Access Sidecar from the Psion

From a Psion browser, use the Android device's reachable network address and port:

```text
http://<android-device-address>:8081/
```

The address depends on the connection being used. It may be the Android device's Wi-Fi address or the address used by a PPP connection.

The browser must be able to reach the Android device over that connection.

## 6. Optional: create an independent test instance

A second instance is useful for testing application updates without disturbing the main service. It has its own application directory, runit service and port.

Install a separate copy of the application:

```sh
cd "$HOME/Psion-sidecar-source"
./scripts/install-termux.sh --target "$HOME/Psion-sidecar-test"
```

Create the test service and logging directories:

```sh
mkdir -p "$PREFIX/var/service/psion-sidecar-test/log"
```

Create its run file:

```sh
cat > "$PREFIX/var/service/psion-sidecar-test/run" <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
cd "$HOME/Psion-sidecar-test" || exit 1
exec "$PREFIX/bin/python" "$HOME/Psion-sidecar-test/sidecar_web.py" --port 8082
EOF
```

Make the run file executable:

```sh
chmod +x "$PREFIX/var/service/psion-sidecar-test/run"
```

Configure the test service logger:

```sh
ln -sf "$PREFIX/share/termux-services/svlogger" \
   "$PREFIX/var/service/psion-sidecar-test/log/run"
```

Enable and start the test service:

```sh
sv-enable psion-sidecar-test
```

Check its status:

```sh
sv status psion-sidecar-test
```

Check its local HTTP response:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8082/
```

A successful response should normally report HTTP status `200`.

Test service output is recorded in:

`$PREFIX/var/log/sv/psion-sidecar-test/current`

To inspect recent log entries:

```sh
tail -n 30 "$PREFIX/var/log/sv/psion-sidecar-test/current"
```

The test service must use:

- Application directory: `~/Psion-sidecar-test`
- Service name: `psion-sidecar-test`
- Port: `8082`

It can run alongside the main instance on port 8081.

Do not point both services at the same application directory or use the same port. The updater checks the service name, application path and port before updating an instance.

## 7. Update an installed instance

The repository includes `scripts/update-termux-sidecar`, a guarded updater that downloads the latest application files from the GitHub `main` branch.

The selected service must already exist and be running. The updater does not create, enable or modify runit service definitions.

For the main instance:

```sh
cd "$HOME/Psion-sidecar-source"

sh scripts/update-termux-sidecar \
  --target "$HOME/Psion-sidecar" \
  --service psion-sidecar \
  --port 8081
```

For the test instance:

```sh
cd "$HOME/Psion-sidecar-source"

sh scripts/update-termux-sidecar \
  --target "$HOME/Psion-sidecar-test" \
  --service psion-sidecar-test \
  --port 8082
```

The updater checks that:

- The target application directory exists.
- The selected runit service exists and is running.
- The service run file references the selected application directory.
- The service run file explicitly specifies the selected port.
- All required application files are present in the GitHub archive.
- Python syntax checks pass.
- The persistent backup is complete and verified before the service is stopped.

It then stops only the selected service, installs the validated files, starts that service and checks its local HTTP response.

The health check accepts HTTP status codes from 200 to 399 and retries if necessary.

If installation or the health check fails, the updater attempts to restore the previous application files and restart the selected service.

The updater does not change crossword data or service definitions.

## 8. Backups and recovery

Persistent updater backups are stored by default in:

`~/.local/share/psion-sidecar/backups/`

Each backup records the GitHub commit, application directory, service name and port, together with copies of the application files that existed before the update.

The updater verifies the backup before stopping the service and retains it after a successful update or rollback.

An alternative backup directory can be selected with `--backup-dir`:

```sh
sh scripts/update-termux-sidecar \
  --target "$HOME/Psion-sidecar" \
  --service psion-sidecar \
  --port 8081 \
  --backup-dir "$HOME/sidecar-backups"
```

**Recovery after a failed update**

If an update fails after the service has been stopped, the updater attempts to restore the previous application files and restart the selected service. The persistent backup is retained.

If restoration or service restart fails, the updater reports a critical error. The service may remain stopped and require manual investigation.

The updater does not currently provide a separate command for manually restoring an earlier successful update. Keep the backup directory intact if you may need to recover an earlier version manually.

Do not delete a backup until the updated instance has been checked.

## 9. Troubleshooting

### Service does not start

Check its status:

```sh
sv status psion-sidecar
```

Check the service run file:

```sh
cat "$PREFIX/var/service/psion-sidecar/run"
```

Check that it references the correct application directory and explicitly specifies port 8081.

Inspect the service log for errors:

```sh
tail -n 30 "$PREFIX/var/log/sv/psion-sidecar/current"
```

### Local HTTP check fails

Check that the main service is running and that the configured port is correct:

```sh
sv status psion-sidecar
curl -v http://127.0.0.1:8081/
```

For the test instance, check its service status and HTTP response:

```sh
sv status psion-sidecar-test
curl -v http://127.0.0.1:8082/
```

Inspect the test-instance service log for errors:

```sh
tail -n 30 "$PREFIX/var/log/sv/psion-sidecar-test/current"
```

For the test instance, use service `psion-sidecar-test` and port `8082`.

### Updater rejects the service

The updater requires the run file to contain the selected application path and an explicit `--port PORT` argument.

The values must match the `--target`, `--service` and `--port` arguments supplied to the updater.

The service must already be running before an update is attempted.

### Software catalogue is incomplete

Check that all three catalogue files are present:

```sh
ls -l "$HOME/Psion-sidecar/"*index.json
```

The required files are `software_index.json`, `epoc16_index.json` and `epoc32_index.json`.

## Security

The Sidecar server has no login or access control and listens on all network interfaces. Use it on a trusted network or controlled connection. Do not expose its HTTP port directly to the public internet.
