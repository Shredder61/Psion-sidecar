# Psion Sidecar

Psion Sidecar is a small Python web server that provides a Psion-friendly homepage hosted on a Raspberry Pi. It brings together Guardian crossword downloads, access to locally stored crossword files, Psion Community software browsing and a Psion-friendly search page. The 'back-office' code is working well, but the homepage display will receive further updates as I develop the content.

The Sidecar can be accessed from a Psion using a compatible browser such as Opera or PsiWeb. The Raspberry Pi provides the web server and connects to the external services used by the project.

The crossword downloader, `guardian_pi.py`, can also be run independently on any suitable computer with Python. This allows you to download crosswords without running the web server. The resulting text files can then be transferred to the Psion and converted using a separate OPL program.

Thank you to Kian (https://www.kianryan.co.uk) and Daniel (https://github.com/danieledge) who created the impetus (connectivity) to get rolling with this after my two 'mint' Psions (one special anniversary 5 (green) and a 5mx) had been in the closet for a decade or so.

## What's included

- Guardian Quick and Cryptic crossword download requests.
- A local text-file archive for downloaded crosswords intended for use with RMR and FatCatz crossword programs on EPOC32.
- A Psion Community software catalogue interface, including filtered program searches and download links.
- A FrogFind search page accessible through the Sidecar.
- An example systemd service for starting the server automatically when the Raspberry Pi boots.
- A separate Psion-side OPL conversion workflow for preparing crossword text for compatible crossword applications.

The project was developed and tested on Raspberry Pi OS with Python 3.13. The Sidecar web server uses Python's standard library and does not require third-party Python packages.

A Raspberry Pi is required to host the browser-based Sidecar, but it is not necessary if you only want to run the standalone crossword downloader.

## Status and limitations

This is a community project provided as-is. The Guardian website, FrogFind and external software archives can change independently of this code. Downloading, searching and catalogue browsing therefore depend on those external services remaining compatible and accessible.

The standalone downloader and browser-based Sidecar are not yet fully aligned, although the intention is to make their interfaces more consistent over time.

The homepage will continue to evolve. Integrating the OPL conversion process more closely into crossword retrieval is a planned improvement.

## Guardian Quick and Cryptic crossword downloads

There are two ways to download Guardian Quick and Cryptic crosswords for use on the Psion:

- **Standalone downloader:** run `guardian_pi.py` directly on a PC or Raspberry Pi.
- **Sidecar downloader:** request downloads through the web interface hosted on a Raspberry Pi, including from a compatible browser on the Psion itself.

I recommend starting with the standalone downloader to understand the download process before using the Sidecar.

Both methods produce a text file that must be converted on the Psion using the appropriate OPL converter before it can be opened in a compatible RMR or FatCatz crossword program.

## Guardian crossword standalone downloader: `guardian_pi.py`

Menu options:
1	Download one crossword
2	Download a batch of crosswords
3	Download today's crossword
4	Exit

Ranges currently displayed in the code are Quick 9093–17583 and Cryptic 21620–30109, based on the archive limits recorded in the source. The “today's crossword” option checks the Guardian for the latest number, so those fixed limits may need updating as the archive grows.

The downloader retrieves the Guardian's accessible, text-based crossword page and saves the puzzle in the text format expected by the Psion OPL converter.

Before downloading, the program checks whether the crossword is already available locally and whether it is present in the Guardian's own archive. If a download is appropriate, it retrieves the puzzle and saves the resulting text file in the output directory.

Example filenames include:

```text
Quick_17028.txt
Cryptic_30103.txt
```

To download a Quick crossword by number, specifying an output directory, run:

```bash
python guardian_pi.py quick 17028 /home/pi/crosswords
```

If no output directory is specified, the program uses its configured default.

### How crosswords are retrieved

The downloader uses the Guardian's accessible crossword pages:

<https://www.theguardian.com/crosswords/accessible/>

It deliberately uses these pages rather than the Guardian's JSON/API interface.

The standalone downloader includes compatibility code for Python 2.7 and Python 3, although Python 3 is recommended. The browser-based web server requires Python 3.

## Guardian crossword Sidecar downloader

The Sidecar web interface uses `guardian_pi.py` to process crossword download requests and presents the results through a browser.

The homepage also provides access to locally stored crossword files, including previously downloaded puzzles.

## Psion Community software Sidecar downloader

Selecting the Psion Community software link on the Sidecar homepage opens a search interface. You can search the software catalogue and obtain download links for matching `.SIS` installer packages.

The catalogue relies on two JSON index files in the project directory:

- `epoc32_index.json`
- `software_index.json`

Both files are included in the current repository. They supply the catalogue data used by the software browsing features.

### Downloading software to the Psion

When you initiate a download, the browser may initially use `Download.bin` as the filename. Wait for the transfer to finish, then select **Save** when prompted. The saved filename should then match the name supplied by the repository.

The downloaded file may retain a `.bin` extension. Follow the behaviour of your Psion browser and installer when saving and installing the file.

The availability of individual packages depends on the external software archive and the links recorded in the catalogue.

Please respect the provenance, copyright and redistribution terms of the indexed material and any linked software packages. Inclusion of catalogue indexes does not grant permission to redistribute the software they describe.

## Quick start: installing the browser-based Sidecar

Clone the repository and enter the project directory:

```bash
git clone https://github.com/Shredder61/Psion-sidecar.git
cd Psion-sidecar
```

Check your Python version and compile-check the scripts:

```bash
python3 --version
python3 -m py_compile sidecar_web.py guardian_pi.py
```

Start the server in the foreground:

```bash
python3 sidecar_web.py
```

From a device on the same network, open:

```text
http://<raspberry-pi-address>:8081/
```

Replace `<raspberry-pi-address>` with the hostname or IP address of your Raspberry Pi.

Stop the foreground server with `Ctrl+C`.

The server listens on `0.0.0.0` on port `8081` by default. Do not expose this port directly to the public internet without appropriate security controls.

## Features of the Sidecar homepage

- Guardian Quick and Cryptic crossword download requests.
- Access to locally stored crossword files.
- Psion Community software catalogue and download links, when the required index data is available.
- FrogFind search access through the Pi.

## Screenshots

The screenshots below show the Sidecar workflow on a Psion, from browsing
files and downloading software to importing a crossword.

![Psion file listing](docs/images/File%20listing%201.png)

![Downloading a software package](docs/images/Download%20in%20progress.png)

![A cryptic crossword after import](docs/images/Imported%20crossword%20-%20cryptic.png)

## Installation as a service

See [docs/INSTALL.md](docs/INSTALL.md) for instructions on installing the server as a systemd service.

See [docs/PSION-SETUP.md](docs/PSION-SETUP.md) for notes on accessing the Sidecar from a Psion.

## Project files

- `sidecar_web.py` — web server
- `guardian_pi.py` — crossword downloader and text formatter
- `systemd/psion-sidecar.service` — example systemd service
- `crosswords/` — local crossword storage
- `docs/` — installation and usage notes
- `epoc32_index.json` - Psion Community software index (EPOC32)
- `software_index.json` - Psion Community software index (complete)
- `crossword converter_v01.TXT` - OPL program for the Psion

## Copyright, permissions and external services

This repository does not grant rights to Guardian crossword content, FrogFind, Psion software packages or third-party catalogue data. Respect the copyright, terms of use and redistribution conditions of each external service and file source.

No project software licence has been selected for this release. Until an appropriate licence is added, do not assume that the code is offered under an open-source licence or that permission to reuse, modify or redistribute it has been granted.
