# Install on Raspberry Pi OS

These instructions assume a Raspberry Pi on a trusted home network, Raspberry Pi OS, Python 3, and an account with `sudo` access.

## 1. Clone the repository

Run these commands on the Raspberry Pi:

```bash
git clone https://github.com/Shredder61/Psion-sidecar.git
cd Psion-sidecar
```

## 2. Install the application files

The server expects its crossword storage directory and all three software catalogue index files to be beside `sidecar_web.py`.

From the repository root, run:

```bash
sudo mkdir -p /opt/psion-sidecar
sudo cp sidecar_web.py guardian_pi.py crossword_converter.py epoc16_index.json epoc32_index.json software_index.json /opt/psion-sidecar/
sudo mkdir -p /opt/psion-sidecar/crosswords
sudo install -m 0644 systemd/psion-sidecar.service /etc/systemd/system/psion-sidecar.service
```

The current GitHub repository includes `epoc16_index.json`, `epoc32_index.json`, and `software_index.json`. If you use a source package that does not include these files, obtain them separately from sources you are authorised to use. The software catalogue will not work fully until all three files are installed beside `sidecar_web.py`.

The service file assumes the installation path `/opt/psion-sidecar`. If you choose another path, edit `WorkingDirectory` and `ExecStart` in `systemd/psion-sidecar.service` before installing it.

## 3. Test the server in the foreground

```bash
cd /opt/psion-sidecar
python3 --version
python3 -m py_compile sidecar_web.py guardian_pi.py crossword_converter.py
python3 sidecar_web.py
```

From another device on the same trusted local network, open:

`http://<raspberry-pi-address>:8081/`

Replace the placeholder with the Raspberry Pi's hostname or IP address. Stop the foreground server with `Ctrl+C` before enabling the service.

If port 8081 is already in use, change `PORT` near the top of `sidecar_web.py` and use the same port in the URL.

## 4. Configure automatic startup

Create the dedicated service account if it does not already exist, then assign ownership of the installation. The application files should be owned by root, but the crossword storage directory must be writable by the `sidecar` service account so that downloads can be saved.

```bash
id sidecar >/dev/null 2>&1 || sudo useradd --system --home-dir /opt/psion-sidecar --shell /usr/sbin/nologin sidecar
sudo chown -R root:root /opt/psion-sidecar
sudo install -d -o sidecar -g sidecar -m 0755 /opt/psion-sidecar/crosswords
sudo systemctl daemon-reload
sudo systemctl enable --now psion-sidecar.service
sudo systemctl status psion-sidecar.service --no-pager
```

**Verify that the service user can write to the crossword directory:**

```bash
sudo -u sidecar test -w /opt/psion-sidecar/crosswords \
  && echo "PASS: Crossword directory is writable" \
  || echo "FAIL: Crossword directory is not writable"
```

The expected result is `PASS`. If it fails, correct the directory ownership and test again:

```bash
sudo chown sidecar:sidecar /opt/psion-sidecar/crosswords
sudo -u sidecar test -w /opt/psion-sidecar/crosswords \
  && echo "PASS: Crossword directory is writable" \
  || echo "FAIL: Crossword directory is not writable"
```

This ownership applies to the `crosswords` directory itself. Do not recursively change ownership of the whole application directory to `sidecar`: the application code and catalogue files should remain root-owned, while the service user needs write access to crossword storage.

View recent service logs with:

```bash
sudo journalctl -u psion-sidecar.service -n 100 --no-pager
```

If the service does not start or a crossword download fails, check the logs. A `PermissionError` or `Permission denied` message involving `crosswords` usually indicates a directory or file permission problem.

## 5. Optional: install the updater

The repository includes `scripts/update-psion-sidecar`, which fetches the latest `main` branch into a temporary staging directory, checks the Python files, backs up the installed application files, updates the service, and checks that the homepage responds. It also checks that the `sidecar` account can write to crossword storage before and after the update. It does not merge or advance your local Git checkout, so a failed installation cannot leave the checkout ahead of the files installed in `/opt/psion-sidecar`.

The script assumes the repository is at `/home/pi/Psion-sidecar` and that the Linux account `pi` owns the Git checkout. If your checkout or account differs, edit `REPO` and `REPO_USER` near the top of the script before installing it.

From the repository root, install it with:

```bash
sudo install -o root -g root -m 0755 scripts/update-psion-sidecar /usr/local/sbin/update-psion-sidecar
```

Run an update with:

```bash
sudo /usr/local/sbin/update-psion-sidecar
```

The updater refuses to proceed if the service is stopped or the Git checkout has uncommitted changes. It stores application backups in `/var/backups/psion-sidecar`. It updates application files but leaves the crossword files and their contents in place. The health check confirms that the homepage responds; it does not test an actual external crossword download. The repository's GitHub Actions workflow runs Bash syntax checks, ShellCheck, and an isolated test of the updater's success and health-check rollback paths.

## Security notes

The server binds to all network interfaces on port 8081 by default and has no login or access control. It is intended for a trusted local network. Do not forward port 8081 from your router to the public internet. Consider firewall rules if the Raspberry Pi is reachable by untrusted devices.
