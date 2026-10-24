# Install on Raspberry Pi OS

These instructions assume a Raspberry Pi on a trusted home network, Python 3, and an account with `sudo` access.

## 1. Install the project

Choose `/opt/psion-sidecar` as the installation directory:

```bash
sudo mkdir -p /opt/psion-sidecar
sudo cp sidecar_web.py guardian_pi.py /opt/psion-sidecar/
sudo mkdir -p /opt/psion-sidecar/crosswords
sudo chown -R "$USER":"$USER" /opt/psion-sidecar
```

Run those commands from the checked-out project directory. If you prefer a different location, update the `ROOT` and index-file paths are already relative to `sidecar_web.py`; also update the `WorkingDirectory` and `ExecStart` values in the service file.

## 2. Test in the foreground

```bash
cd /opt/psion-sidecar
python3 -m py_compile sidecar_web.py guardian_pi.py
python3 sidecar_web.py
```

From another device on the same LAN, open `http://<raspberry-pi-address>:8081/`. Stop the foreground server with `Ctrl+C` before enabling the service.

If port 8081 is already in use, change `PORT` near the top of `sidecar_web.py` and use the same port in the URL.

## 3. Configure automatic startup

The example service uses a dedicated account named `sidecar`. Create it and assign ownership:

```bash
sudo useradd --system --home-dir /opt/psion-sidecar --shell /usr/sbin/nologin sidecar
sudo chown -R sidecar:sidecar /opt/psion-sidecar
sudo install -m 0644 systemd/psion-sidecar.service /etc/systemd/system/psion-sidecar.service
sudo systemctl daemon-reload
sudo systemctl enable --now psion-sidecar.service
sudo systemctl status psion-sidecar.service --no-pager
```

If you have already installed the files under a different path, edit `/etc/systemd/system/psion-sidecar.service` to match your actual installation directory before starting it.

View logs with:

```bash
sudo journalctl -u psion-sidecar.service -n 100 --no-pager
```

## 4. Optional software catalogue data

The software catalogue routes expect `epoc32_index.json` and `software_index.json` beside `sidecar_web.py`. These files are not shipped in the repository. Only install data that you are authorised to use, and do not commit large or third-party data files without checking redistribution rights.

## Security notes

The server is designed for a trusted local network. It has no login or access control and binds to all network interfaces by default. Do not port-forward port 8081 from your router to the public internet. Consider a firewall if the Pi is on a network shared with untrusted devices.
