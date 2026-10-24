# Install on Raspberry Pi OS

These instructions assume a Raspberry Pi on a trusted home network, Raspberry Pi OS, Python 3, and an account with `sudo` access.

## 1. Clone the repository

Run these commands on the Raspberry Pi:

```bash
git clone https://github.com/Shredder61/Psion-sidecar.git
cd Psion-sidecar
```

## 2. Install the application files

The server expects its crossword storage directory and, for the software catalogue, both JSON indexes to be beside `sidecar_web.py`.

From the repository root, run:

```bash
sudo mkdir -p /opt/psion-sidecar
sudo cp sidecar_web.py guardian_pi.py epoc32_index.json software_index.json /opt/psion-sidecar/
sudo mkdir -p /opt/psion-sidecar/crosswords
sudo install -m 0644 systemd/psion-sidecar.service /etc/systemd/system/psion-sidecar.service
sudo chown -R "$USER":"$USER" /opt/psion-sidecar
```

The current GitHub repository includes `epoc32_index.json` and `software_index.json`. If you use a source package that does not include them, omit those two filenames from the `cp` command and obtain the index files separately from sources you are authorised to use. The software catalogue will not work until both files are installed beside `sidecar_web.py`.

The service file assumes the installation path `/opt/psion-sidecar`. If you choose another path, edit `WorkingDirectory` and `ExecStart` in `systemd/psion-sidecar.service` before installing it.

## 3. Test the server in the foreground

```bash
cd /opt/psion-sidecar
python3 --version
python3 -m py_compile sidecar_web.py guardian_pi.py
python3 sidecar_web.py
```

From another device on the same trusted local network, open:

`http://<raspberry-pi-address>:8081/`

Replace the placeholder with the Raspberry Pi's hostname or IP address. Stop the foreground server with `Ctrl+C` before enabling the service.

If port 8081 is already in use, change `PORT` near the top of `sidecar_web.py` and use the same port in the URL.

## 4. Configure automatic startup

Create the dedicated service account if it does not already exist, then assign ownership of the installation:

```bash
id sidecar >/dev/null 2>&1 || sudo useradd --system --home-dir /opt/psion-sidecar --shell /usr/sbin/nologin sidecar
sudo chown -R sidecar:sidecar /opt/psion-sidecar
sudo systemctl daemon-reload
sudo systemctl enable --now psion-sidecar.service
sudo systemctl status psion-sidecar.service --no-pager
```

View recent service logs with:

```bash
sudo journalctl -u psion-sidecar.service -n 100 --no-pager
```

If the service does not start, check the log output before trying again.

## Security notes

The server binds to all network interfaces on port 8081 by default and has no login or access control. It is intended for a trusted local network. Do not forward port 8081 from your router to the public internet. Consider firewall rules if the Raspberry Pi is reachable by untrusted devices.
