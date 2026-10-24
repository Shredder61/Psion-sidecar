# Psion Sidecar

A small Python web server intended to provide a Psion-friendly homepage on a Raspberry Pi. The project includes:

- Guardian Quick and Cryptic crossword download requests and a text-file archive
- A Psion software catalogue interface, when the catalogue index files are supplied
- A FrogFind proxy page
- A systemd service example for running the server at boot

The project was developed and tested on Raspberry Pi OS with Python 3.13. The server uses Python's standard library and does not require a third-party Python package.

## Status and limitations

This is a community project, provided as-is. The Guardian website, FrogFind and external software archives can change independently of this code. Download and catalogue behaviour therefore depends on those external services remaining compatible and accessible.

The software catalogue requires two data files in the project directory:

- `epoc32_index.json`
- `software_index.json`

They are intentionally **not included** in this source release. Obtain or generate them from sources you are entitled to use, and check their provenance and redistribution terms before publishing them. Without these files, the crossword features can still be used, but the software catalogue endpoints will show an error.

Downloaded crossword files are also not included. The `crosswords/` directory is created for local downloads.

## Quick start

```bash
git clone <YOUR-REPOSITORY-URL> psion-sidecar
cd psion-sidecar
python3 --version
python3 -m py_compile sidecar_web.py guardian_pi.py
python3 sidecar_web.py
```

Open `http://<raspberry-pi-address>:8081/` from a device on the same network. Stop the foreground server with `Ctrl+C`.

The server binds to `0.0.0.0` on port `8081` by default. Do not expose this port directly to the public internet without adding appropriate security controls.

## Features

- Homepage with links to local crossword files and download forms
- Quick and Cryptic crossword download by puzzle number
- Local crossword archive
- FrogFind access through the Pi
- Psion software catalogue pages when the required index data is installed

## Installation as a service

See [docs/INSTALL.md](docs/INSTALL.md) for a dedicated systemd installation. See [docs/PSION-SETUP.md](docs/PSION-SETUP.md) for use from a Psion.

## Project files

- `sidecar_web.py` — web server
- `guardian_pi.py` — crossword downloader and text formatter
- `systemd/psion-sidecar.service` — example systemd service
- `crosswords/` — local crossword storage
- `docs/` — installation and usage notes

## Copyright, permissions and external services

This repository contains the Sidecar project code only. It does not grant rights to Guardian content, FrogFind, Psion software packages, or third-party catalogue data. Respect the terms and copyright of each external service and file source.

No project licence has been selected in this release. Before inviting others to reuse, modify or redistribute the code, the maintainer should choose and add an appropriate licence for code they have the right to license.
