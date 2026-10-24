# Psion Sidecar

A small Python web server intended to provide a Psion-friendly homepage on a Raspberry Pi. The Pi (Sidecar) implementation gives visibility of downloaded files, today's Guardian crossword download, as well as access to the Psion community software (direct download of filtered programs) and a Psion-friendly search page, which can be accessed using Opera or PsiWeb from your Psion device.

Of course, the Py crossword program (guardian_pi.py) can be run independently to pull crosswords from a computer with Python which you can then convert with the provided OPL converter.

The Sidecar project includes:

- Guardian Quick and Cryptic crossword download requests and a text-file archive for RMR / FatCatz crosswords (EPOC32)
- A Psion software catalogue interface
- A FrogFind proxy page
- A systemd service example for running the Pi server at boot
- An OPL program (Psion) which transcribes the downloaded crossword text file into the required format for RMR/FatCatz programs

The project was developed and tested on Raspberry Pi OS with Python 3.13. The Sidecar server uses Python's standard library and does not require a third-party Python package. A Raspberry Pi is required to host the browser-based Sidecar, but is not essential to run the standalone crossword downloader, if that's all you need.

## Status and limitations

This is a community project, provided as-is. The Guardian website, FrogFind and external software archives can change independently of this code. Download and catalogue behaviour therefore depends on those external services remaining compatible and accessible. The OPL program will at some point be integrated into the Crossword text file retrieval. The Home page will be revised/improved. 

## Guardian Quick and Cryptic crossword downloads

There are two ways to download Guardian Quick and Cryptic crosswords for use on the Psion:

- **Standalone downloader:** Run `guardian_pi.py` directly on a PC or Raspberry Pi.
- **Sidecar downloader:** Request downloads through the web interface hosted on a Raspberry Pi, including from a compatible browser on the Psion itself.

The two interfaces are not yet fully aligned, although they are intended to become more similar over time. I recommend starting with the standalone downloader to understand how the download process works before using the Sidecar. The output text file for either needs to be converted using the provided OPL converter on the Psion.

## Guardian crossword standalone downloader: `guardian_pi.py`

The downloader retrieves the Guardian's accessible, text-based crossword page and converts the puzzle into the text format expected by the Psion OPL converter, ready for opening in the RMR / FatCatz crossword program.

Before downloading, the program checks whether the crossword is already available locally and whether it is present in the Guardian's own archive. If a download is appropriate, it retrieves the puzzle and saves the resulting text file in the specified output directory.

Downloaded files use names such as:

```text
Quick_17028.txt
Cryptic_30103.txt
```

You can specify the crossword type and number, and optionally the output directory. For example:

```bash
python guardian_pi.py quick 17028 /home/pi/crosswords
```

If no output directory is specified, the program uses its configured default.

### How it retrieves crosswords

The downloader uses the Guardian's accessible crossword pages:

`https://www.theguardian.com/crosswords/accessible/...`

It deliberately uses these pages rather than the Guardian's JSON/API interface.

The script is compatible with Python 2.7 and Python 3.

## Guardian crossword Sidecar downloader

This runs the same guardian_pi.py program and presents the results in the browser.

## Psion Community software Sidecar downloader

When you select the Psion Community software link on the homepage it will load a search box. The software will locate .SIS installer files and present you with one or more download links. When you initiate a download, the default filename is Download.bin - wait for the file to transfer and then select "Save", the filename will then match the repository name. You can run it as a .bin file and it will be correctly recognised by your installer.

The software catalogue uses two index files in the project directory:

- `epoc32_index.json`
- `software_index.json`

Both files are included in this release. They provide the catalogue data used by the Psion Community software browsing features. Please respect the provenance, copyright and redistribution terms of the indexed material and any linked software packages.

## Quick start - Installing the browser-based Sidecar

```bash
git clone <YOUR-REPOSITORY-URL> psion-sidecar
cd psion-sidecar
python3 --version
python3 -m py_compile sidecar_web.py guardian_pi.py
python3 sidecar_web.py
```

Open `http://<raspberry-pi-address>:8081/` from a device on the same network. Stop the foreground server with `Ctrl+C`.

The server binds to `0.0.0.0` on port `8081` by default. Do not expose this port directly to the public internet without adding appropriate security controls.

## Features of the Sidecar homepage

- Psion software catalogue pages (requires index data)
- FrogFind access through the Pi
- Quick and Cryptic crossword download by puzzle number
- Local crossword archive

## Installation as a service

See [docs/INSTALL.md](docs/INSTALL.md) for a dedicated systemd installation. See [docs/PSION-SETUP.md](docs/PSION-SETUP.md) for use from a Psion.

## Project files

- `sidecar_web.py` — web server
- `guardian_pi.py` — crossword downloader and text formatter
- `systemd/psion-sidecar.service` — example systemd service
- `crosswords/` — local crossword storage
- `docs/` — installation and usage notes
- '

## Copyright, permissions and external services

This repository contains the Sidecar project code only. It does not grant rights to Guardian content, FrogFind, Psion software packages, or third-party catalogue data. Respect the terms and copyright of each external service and file source.

No project licence has been selected in this release. Before inviting others to reuse, modify or redistribute the code, the maintainer should choose and add an appropriate licence for code they have the right to license.
