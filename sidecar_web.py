#!/usr/bin/env python3

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import html
from urllib.parse import urlparse, unquote, parse_qs, quote
import re
from urllib.request import Request, urlopen
import json
from functools import lru_cache


HOST = "0.0.0.0"
PORT = 8081


def _normalise_package_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _find_package_archive(item_filename, references):
    """Choose a ZIP relevant to this installer, not a shared dependency."""
    from urllib.parse import unquote_plus

    archive_extensions = (".zip", ".iso", ".tar", ".7z", ".rar")
    item_stem = item_filename.rsplit(".", 1)[0]
    item_token = _normalise_package_name(item_stem)

    # Build aliases from references to this item, including references
    # without URLs, such as "banktran/s3export.app".
    aliases = set()

    for reference in references:
        reference_name = unquote_plus(
            str(reference.get("name", ""))
        ).replace("\\", "/")

        url = reference.get("url", "")
        url_path = urlparse(url).path if url else ""
        url_leaf = (
            unquote_plus(url_path.rsplit("/", 1)[-1])
            if url_path else ""
        )
        name_leaf = reference_name.rsplit("/", 1)[-1]

        if (
            name_leaf.lower() == item_filename.lower()
            or url_leaf.lower() == item_filename.lower()
        ):
            name_parts = reference_name.split("/")
            for part in name_parts[-2:-1]:
                part = part.strip()
                if part and not part.lower().endswith(archive_extensions):
                    token = _normalise_package_name(part)
                    if token:
                        aliases.add(token)

    candidates = []

    for position, reference in enumerate(references):
        url = reference.get("url", "")
        if not url:
            continue

        parsed = urlparse(url)
        url_path = parsed.path

        reference_name = unquote_plus(
            str(reference.get("name", ""))
        ).replace("\\", "/")

        if not reference_name:
            reference_name = unquote_plus(
                url_path.rsplit("/", 1)[-1]
            )

        archive_name = reference_name.rsplit("/", 1)[-1]

        if not archive_name.lower().endswith(".zip"):
            continue

        path_parts = url_path.split("/")
        has_archive_parent = any(
            unquote_plus(part).lower().endswith(archive_extensions)
            for part in path_parts[:-1]
        )

        host = (parsed.hostname or "").lower()

        archive_org_nested_zip = (
            has_archive_parent
            and (
                host == "archive.org"
                or host.endswith(".archive.org")
            )
            and any(
                unquote_plus(part).lower().endswith((".zip", ".iso"))
                for part in path_parts[:-1]
            )
        )

        # Do not treat arbitrary nested files as package downloads.
        if has_archive_parent and not archive_org_nested_zip:
            continue

        archive_stem = archive_name.rsplit(".", 1)[0]
        archive_token = _normalise_package_name(archive_stem)

        if not archive_token:
            continue

        score = 0

        # A matching archive name is the strongest evidence.
        if archive_token == item_token:
            score = 100
        elif item_token and (
            item_token in archive_token or archive_token in item_token
        ):
            score = 90

        # Allow a differently named ZIP when its name matches a directory
        # containing the actual installer, e.g. BANKTRAN/S3EXPORT.APP.
        if archive_token in aliases:
            score = max(score, 80)

        if score:
            # Prefer a specific nested package over an equally named
            # top-level reference.
            if archive_org_nested_zip:
                score += 5

            candidates.append((score, -position, reference))

    if not candidates:
        return None

    candidates.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return candidates[0][2]


BASE_DIR = Path(__file__).resolve().parent
ROOT = BASE_DIR / "crosswords"

# Language names and common native-language spellings seen in software records.
# Keep this deliberately explicit: do not guess language from arbitrary suffixes.
_LANGUAGE_ALIASES = {
    "English": ("english", "englisch", "ingles", "inglés", "inglese", "eng"),
    "French": ("french", "français", "francais", "francese", "französisch", "franzosisch", "fr"),
    "German": ("german", "deutsch", "deutsche", "tedesco", "alemán", "aleman", "de"),
    "Spanish": ("spanish", "español", "espanol", "spagnolo", "spanisch", "castellano", "es"),
    "Italian": ("italian", "italiano", "italienisch", "it"),
    "Dutch": ("dutch", "nederlands", "neerlandés", "neerlandes", "hollands", "nl"),
    "Portuguese": ("portuguese", "português", "portugues", "portoghese", "pt"),
    "Swedish": ("swedish", "svenska", "schwedisch", "sv"),
    "Norwegian": ("norwegian", "norsk", "norwegisch", "no"),
    "Danish": ("danish", "dansk", "dänisch", "daenisch", "da"),
    "Finnish": ("finnish", "suomi", "finnisch", "fi"),
    "Russian": ("russian", "русский", "russisch", "ru"),
    "Polish": ("polish", "polski", "polnisch", "pl"),
    "Czech": ("czech", "čeština", "cestina", "tschechisch", "cz"),
    "Hungarian": ("hungarian", "magyar", "ungarisch", "hu"),
    "Greek": ("greek", "ελληνικά", "griechisch", "el"),
    "Turkish": ("turkish", "türkçe", "turkce", "tr"),
    "Japanese": ("japanese", "日本語", "jp", "ja"),
    "Chinese": ("chinese", "中文", "zh"),
    "Korean": ("korean", "한국어", "ko"),
}


def _language_matches(text):
    """Return canonical languages explicitly named in text, in stable order."""
    text = str(text or "").casefold()
    found = []
    for language, aliases in _LANGUAGE_ALIASES.items():
        for alias in aliases:
            # The item-aligned audit excludes ambiguous short codes.
            if len(alias) <= 2:
                continue
            pattern = r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])"
            if re.search(pattern, text, re.IGNORECASE):
                found.append(language)
                break
    return found

# Program IDs classified by the item-aligned audit as shared system dependencies.
_SHARED_LANGUAGE_EXCLUSIONS = {
    "uid/0x10000b90",  # Systinfo OPX
    "uid/0x10000405",  # Sysram1 OPX
    "uid/0x10000002",  # SysRAM1.opx
    "uid/0x00000000",  # SysRam1.opx
    "uid/0x10000079",  # SysRAM1 application
    "uid/0x00003039",  # sysram1
}


def _languages_for_catalogue_item(program_id, item):
    """Return languages supported by this specific catalogue item only."""
    from urllib.parse import unquote_plus

    if str(program_id) in _SHARED_LANGUAGE_EXCLUSIONS:
        return []

    item_text = " ".join((
        str(item.get("name", "") or ""),
        str(item.get("filename", "") or ""),
    ))
    found = _language_matches(item_text)
    if found:
        return found

    short_codes = {
        "EN": "English", "FR": "French", "DE": "German", "IT": "Italian",
        "ES": "Spanish", "NL": "Dutch", "PT": "Portuguese", "SV": "Swedish",
        "NO": "Norwegian", "DA": "Danish", "FI": "Finnish", "RU": "Russian",
        "PL": "Polish", "CZ": "Czech", "HU": "Hungarian", "EL": "Greek",
        "GR": "Greek", "TR": "Turkish", "JA": "Japanese", "JP": "Japanese",
        "ZH": "Chinese", "KO": "Korean",
    }
    filename = str(item.get("filename", "") or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    match = re.match(r"^([A-Z]{2})[-_]", stem, re.IGNORECASE)
    if match and match.group(1).upper() in short_codes:
        return [short_codes[match.group(1).upper()]]
    match = re.search(r"(?:[-_]|[0-9])([A-Z]{2})$", stem, re.IGNORECASE)
    if match and match.group(1).upper() in short_codes:
        return [short_codes[match.group(1).upper()]]

    def path_languages(path_text):
        results = []
        decoded = unquote_plus(str(path_text or "")).replace("\\", "/")
        for component in [part for part in decoded.split("/") if part]:
            for language in _language_matches(component):
                if language not in results:
                    results.append(language)
        return results

    references = item.get("references", item.get("reference", [])) or []
    results = []
    normal_stem = re.sub(r"[^a-z0-9]", "", stem.casefold())
    for reference in references:
        ref_url = str(reference.get("url", "") or "")
        if not ref_url:
            continue
        path = unquote_plus(str(urlparse(ref_url).path)).replace("\\\\", "/")
        normal_path = re.sub(r"[^a-z0-9]", "", path.casefold())
        if normal_stem and len(normal_stem) >= 4 and normal_stem not in normal_path:
            continue
        for language in path_languages(path):
            if language not in results:
                results.append(language)
    return results


def _program_language_versions(program):
    """Return language/version pairs supported by the specific catalogue items.

    Evidence is evaluated per item: item metadata first, then language-specific
    path components in that item's own references. Archive titles and unrelated
    reference names are deliberately not used as evidence.
    """
    from urllib.parse import unquote_plus

    program_id = str(program.get("id", "") or "")
    result = []
    seen = set()

    # Explicit short-code patterns are accepted only in filenames with clear
    # language-edition structure (e.g. FR-ISP.SIS, MSGSUITE10FR.ZIP).
    short_codes = {
        "EN": "English", "FR": "French", "DE": "German", "IT": "Italian",
        "ES": "Spanish", "NL": "Dutch", "PT": "Portuguese", "SV": "Swedish",
        "NO": "Norwegian", "DA": "Danish", "FI": "Finnish", "RU": "Russian",
        "PL": "Polish", "CZ": "Czech", "HU": "Hungarian", "EL": "Greek",
        "GR": "Greek", "TR": "Turkish", "JA": "Japanese", "JP": "Japanese",
        "ZH": "Chinese", "KO": "Korean",
    }

    def explicit_filename_code(text):
        text = str(text or "").replace("\\", "/").rsplit("/", 1)[-1]
        stem = text.rsplit(".", 1)[0]
        # A leading code followed by a separator, or a trailing code preceded
        # by a separator/digit, is specific enough to indicate an edition.
        m = re.match(r"^([A-Z]{2})[-_]", stem, re.IGNORECASE)
        if m and m.group(1).upper() in short_codes:
            return [short_codes[m.group(1).upper()]]
        m = re.search(r"(?:[-_]|[0-9])([A-Z]{2})$", stem, re.IGNORECASE)
        if m and m.group(1).upper() in short_codes:
            return [short_codes[m.group(1).upper()]]
        return []

    def path_component_languages(path_text):
        found = []
        # Decode escaped archive-internal paths and plus-encoded spaces.
        decoded = unquote_plus(str(path_text or "")).replace("\\", "/")
        for component in [c for c in decoded.split("/") if c]:
            # Long, explicit language names only; do not scan whole archive
            # paths where a language word may refer to unrelated content.
            for language in _language_matches(component):
                if language not in found:
                    found.append(language)
        return found

    for version in program.get("versions", []) or []:
        version_label = str(version.get("version") or "Unknown").strip() or "Unknown"
        version_languages = []

        for variant in version.get("variants", []) or []:
            for item in variant.get("items", []) or []:
                for language in _languages_for_catalogue_item(program_id, item):
                    if language not in version_languages:
                        version_languages.append(language)

        languages = version_languages or ["Language not identified"]
        for language in languages:
            pair = (language, version_label)
            if pair not in seen:
                seen.add(pair)
                result.append(pair)

    if not result:
        result.append(("Language not identified", "Unknown"))
    return result


@lru_cache(maxsize=1)
def _load_software_catalogue():
    """Load the full catalogue once for version and language annotations."""
    with open(BASE_DIR / "software_index.json", "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _software_catalogue_by_id():
    """Index the full software catalogue by program ID."""
    return {
        str(program.get("id", "")): program
        for program in _load_software_catalogue()
    }


@lru_cache(maxsize=8192)
def _cached_program_language_versions(program_id):
    """Cache language/version annotations for each catalogue program."""
    program = _software_catalogue_by_id().get(str(program_id))
    if program is None:
        return (("Language not identified", "Unknown"),)
    return tuple(_program_language_versions(program))

class SidecarHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/" or path == "/refresh":
            self.send_homepage()
        elif path == "/guardian-crossword":
            self.send_guardian_crossword()
        elif path == "/request":
            self.handle_request(query)
        elif path == "/rmr":
            self.handle_rmr(query)
        elif path == "/frogfind":
            self.handle_frogfind(query)
        elif path == "/psionsoftware":
            self.handle_psionsoftware(query)
        elif path == "/psionprogram":
            self.handle_psionprogram(query)
        elif path == "/psiondownload" or path.startswith("/psiondownload/"):
            self.handle_psiondownload(self.path)
        else:
            super().do_GET()

    def handle_frogfind(self, query):
        url = "https://frogfind.de/"

        if query:
            from urllib.parse import urlencode
            url += "?" + urlencode(query, doseq=True)

        try:
            req = Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            with urlopen(req, timeout=15) as response:
                data = response.read()

            text = data.decode("utf-8", errors="replace")

            text = text.replace(
                '<form action="./" method="get">',
                '<form action="/frogfind" method="get">'
            )

            text = text.replace(
                "https://frogfind.de/",
                "/frogfind"
            )

            text = text.replace(
                "http://frogfind.de/",
                "/frogfind"
            )

            data = text.encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.send_header(
                "Cache-Control",
                "no-store"
            )
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            message = (
                "<html><body>"
                "<h1>FrogFind error</h1>"
                "<p>Could not contact FrogFind.</p>"
                "<p><a href='/'>Back to Sidecar</a></p>"
                "</body></html>"
            )

            data = message.encode("utf-8")

            self.send_response(502)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.end_headers()
            self.wfile.write(data)


    def handle_psionsoftware(self, query):
        try:
            platform = query.get("platform", ["epoc32"])[0].strip().lower()

            if platform not in ("epoc16", "epoc32"):
                platform = "epoc32"

            index_file = BASE_DIR / f"{platform}_index.json"

            with open(index_file, "r", encoding="utf-8") as f:
                programs = json.load(f)

            filter_text = query.get("q", [""])[0].strip().lower()

            if filter_text:
                programs = [
                    program for program in programs
                    if filter_text in program.get("name", "").lower()
                ]

            programs.sort(
                key=lambda program: program.get("name", "").lower()
            )

            rows = []

            for indexed_program in programs:
                name = html.escape(indexed_program.get("name", ""))
                program_id = html.escape(
                    str(indexed_program.get("id", "")), quote=True
                )

                rows.append(
                    '<p><a href="/psionprogram?id='
                    + program_id
                    + '">'
                    + name
                    + '</a></p>'
                )

            if not rows:
                rows.append("<p>No programs found.</p>")

            epoc16_selected = " selected" if platform == "epoc16" else ""
            epoc32_selected = " selected" if platform == "epoc32" else ""

            page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Psion Software</title>
</head>
<body>

<h1>PSION SOFTWARE</h1>

<form action="/psionsoftware" method="get">
<p>
Platform:
<select name="platform">
<option value="epoc16"{epoc16_selected}>EPOC16 (Series 3)</option>
<option value="epoc32"{epoc32_selected}>EPOC32 (Series 5/5mx)</option>
</select>
</p>
<p>
Filter:
<input type="text"
       name="q"
       value="{html.escape(filter_text, quote=True)}"
       size="20">
<input type="submit" value="FILTER">
</p>
</form>

<hr>

<p>{len(programs)} programs</p>

{chr(10).join(rows)}

<hr>

<p>
<a href="/">BACK TO SIDECAR</a>
</p>

</body>
</html>
"""

            data = page.encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.send_header(
                "Cache-Control",
                "no-store"
            )
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            print("Psion Software error:", repr(e))

            message = (
                "<html><body>"
                "<h1>Psion Software error</h1>"
                "<p>Could not load the Psion Software Index.</p>"
                "<p><a href='/'>Back to Sidecar</a></p>"
                "</body></html>"
            )

            data = message.encode("utf-8")

            self.send_response(502)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.end_headers()
            self.wfile.write(data)

    def handle_psionprogram(self, query):
        from urllib.parse import quote

        program_id = query.get("id", [""])[0]

        if not program_id:
            self.send_error(400, "Missing program ID")
            return

        try:
            with open(
                BASE_DIR / "software_index.json",
                "r",
                encoding="utf-8"
            ) as f:
                programs = json.load(f)

            program = None

            for item in programs:
                if item.get("id", "") == program_id:
                    program = item
                    break

            if program is None:
                self.send_error(404, "Program not found")
                return

            name = html.escape(
                program.get("name", "")
            )

            platforms = ", ".join(
                program.get("platforms", [])
            )

            runtimes = ", ".join(
                program.get("runtimes", [])
            )

            language_versions = _cached_program_language_versions(program_id)
            languages = ", ".join(dict.fromkeys(
                language for language, _version in language_versions
                if language != "Language not identified"
            ))
            if not languages:
                languages = "English likely"

            unique_files = {}

            for version in program.get("versions", []):

                version_number = version.get(
                    "version", ""
                )

                for variant in version.get("variants", []):

                    for item in variant.get("items", []):

                        filename = item.get(
                            "filename", ""
                        )

                        size = item.get("size")

                        sha256 = item.get(
                            "sha256", ""
                        )

                        if sha256:
                            key = sha256
                        else:
                            key = (
                                filename,
                                version_number,
                                size
                            )

                        download_url = None
                        package_url = None

                        archive_extensions = (
                            ".zip", ".iso", ".tar", ".7z", ".rar"
                        )

                        if item.get("kind") in (
                            "installer",
                            "standalone"
                        ):
                            for reference in item.get("references", item.get("reference", [])):
                                reference_url = reference.get("url")

                                if not reference_url:
                                    continue

                                reference_path = urlparse(
                                    reference_url
                                ).path.lower()

                                path_parts = reference_path.split("/")

                                has_archive_parent = any(
                                    part.endswith(archive_extensions)
                                    for part in path_parts[:-1]
                                )

                                # Archive.org can serve individual files
                                # from inside an ISO using nested-file URLs.
                                archive_host = (
                                    urlparse(reference_url).hostname or ""
                                ).lower()

                                archive_org_nested_file = (
                                    has_archive_parent
                                    and (
                                        archive_host == "archive.org"
                                        or archive_host.endswith(".archive.org")
                                    )
                                    and any(
                                        part.lower().endswith((".zip", ".iso"))
                                        for part in path_parts[:-1]
                                    )
                                )

                                # Offer direct SIS, APP and OPA references,
                                # including individual files inside verified
                                # Archive.org ZIP/ISO collections.
                                if reference_path.endswith(".sis"):
                                    if (
                                        not has_archive_parent
                                        or archive_org_nested_file
                                    ):
                                        download_url = reference_url
                                        break

                                if reference_path.endswith((".app", ".opa")):
                                    if (
                                        not has_archive_parent
                                        or archive_org_nested_file
                                    ):
                                        download_url = reference_url
                                        break




                        if item.get("kind") in ("installer", "standalone"):
                            selected_package_reference = _find_package_archive(
                                filename,
                                item.get("references", item.get("reference", []))
                            )
                            if selected_package_reference:
                                package_url = selected_package_reference.get("url")

                        candidate = {
                            "filename": filename,
                            "version": version_number,
                            "size": size,
                            "sha256": sha256,
                            "kind": item.get("kind", ""),
                            "languages": ", ".join(_languages_for_catalogue_item(program_id, item)) or "English likely",
                            "download_url": download_url,
                            "package_url": package_url,
                            "references": list(
                                item.get("references", item.get("reference", [])) or []
                            )
                        }

                        existing = unique_files.get(key)

                        if existing is None:

                            unique_files[key] = candidate

                        else:
                            # Preserve the source references from every catalogue
                            # entry represented by this deduplicated file row.
                            existing_references = existing.setdefault("references", [])
                            known_references = {
                                (str(ref.get("name", "")), str(ref.get("url", "") or ""))
                                for ref in existing_references
                            }
                            for reference in candidate.get("references", []):
                                reference_key = (
                                    str(reference.get("name", "")),
                                    str(reference.get("url", "") or "")
                                )
                                if reference_key not in known_references:
                                    existing_references.append(reference)
                                    known_references.add(reference_key)

                            if (
                                candidate["download_url"]
                                and not existing["download_url"]
                            ):
                                unique_files[key] = candidate

                            elif (
                                candidate["download_url"]
                                and existing["download_url"]
                                and candidate["filename"].startswith(
                                    "EPOC - "
                                )
                                and not existing["filename"].startswith(
                                    "EPOC - "
                                )
                            ):
                                unique_files[key] = candidate

                            elif (
                                candidate["package_url"]
                                and not existing["package_url"]
                            ):
                                existing["package_url"] = candidate["package_url"]

            rows = []

            for item in unique_files.values():

                filename = html.escape(
                    item["filename"]
                )

                version_number = html.escape(
                    item["version"]
                )

                size = item["size"]

                if size:
                    size_text = (
                        str(round(size / 1024))
                        + " KB"
                    )
                else:
                    size_text = ""

                if item["kind"] == "installer":
                    kind = "SIS installer"
                else:
                    kind = html.escape(
                        item["kind"]
                    )


                if item.get("package_url") and not item.get("download_url"):
                    display_filename = (
                        filename.rsplit(".", 1)[0]
                        + " — COMPLETE PACKAGE (.ZIP)"
                    )
                    display_kind = "Package download only"
                    display_size = ""
                else:
                    display_filename = filename
                    display_kind = kind
                    display_size = size_text

                rows.append(
                    "<p>"
                    + "<strong>"
                    + html.escape(display_filename)
                    + "</strong><br>"
                    + "Version: "
                    + html.escape(version_number)
                    + "<br>"
                    + html.escape(display_kind)
                    + "<br>Language: "
                    + html.escape(item.get("languages") or "English likely")
                    + (
                        "<br>" + html.escape(display_size)
                        if display_size
                        else ""
                    )
                )


                if item.get("package_url"):
                    package_href = (
                        "/psiondownload/PACKAGE.ZIP?id="
                        + quote(program_id, safe="")
                        + "&h="
                        + quote(item["sha256"][:8], safe="")
                    )

                    rows.append(
                        '<br><a href="'
                        + html.escape(package_href, quote=True)
                        + '">DOWNLOAD COMPLETE .ZIP PACKAGE (RECOMMENDED)</a>'
                    )

                if item["download_url"]:

                    download_href = (
                        "/psiondownload/DOWNLOAD.BIN?id="
                        + quote(
                            program_id,
                            safe=""
                        )
                        + "&h="
                        + quote(
                            item["sha256"][:8],
                            safe=""
                        )
                    )

                    rows.append(
                        '<br><a href="'
                        + html.escape(
                            download_href,
                            quote=True
                        )

                        + '">'
                        + (
                            "DOWNLOAD INDIVIDUAL FILE (.OPA/.APP) "
                            "[NOTE, .ZIP IS PREFERABLE]"
                            if item["filename"].lower().endswith((".opa", ".app"))
                            else "DOWNLOAD SIS INSTALLER"
                            if item["filename"].lower().endswith(".sis")
                            else "DOWNLOAD INDIVIDUAL FILE"
                        )
                        + '</a>'

                    )

                    original_filename = item["filename"].lower()

                    if original_filename.endswith(".sis"):
                        instruction = (
                            "After downloading, rename .bin to .sis, "
                            "then open the file to install."
                        )

                    elif original_filename.endswith(".app"):
                        instruction = (
                            "After downloading, rename .bin to .app."
                        )

                    elif original_filename.endswith(".opa"):
                        instruction = (
                            "After downloading, rename .bin to .opa."
                        )

                    else:
                        instruction = (
                            "After downloading, rename .bin to the "
                            "original file extension."
                        )

                    rows.append(
                        '<br><small>'
                        + instruction
                        + '</small>'
                    )

                # Show useful source references without exposing direct links to
                # potentially very large archive downloads. This is display-only:
                # the existing download-selection logic above remains unchanged.
                references = item.get("references", []) or []
                if references:
                    rendered_refs = []
                    item_size = item.get("size")
                    try:
                        item_size = int(item_size) if item_size is not None else None
                    except (TypeError, ValueError):
                        item_size = None
                    max_reference_file_bytes = 10 * 1024 * 1024
                    archive_extensions = (".zip", ".iso", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz")
                    program_extensions = (".sis", ".app", ".opa")

                    # Preserve catalogue order. A source-page reference begins a
                    # source group; archive references become parents for the
                    # following file/path references until another archive appears.
                    source_groups = []
                    current_group = {"title": "Other references", "source_url": "", "entries": []}
                    source_groups.append(current_group)
                    current_archive = None
                    top_archive = None

                    for reference in references:
                        reference_name = str(reference.get("name", "") or "").strip()
                        reference_url = str(reference.get("url", "") or "").strip()
                        safe_url = urlparse(reference_url)
                        decoded_path = unquote(safe_url.path)
                        decoded_path_lower = decoded_path.lower()
                        if not reference_name:
                            reference_name = reference_url or "Unnamed reference"
                        lowered_name = unquote(reference_name).lower()
                        is_nested_archive_path = (
                            "/download/" in safe_url.path.lower()
                            and any(ext in decoded_path_lower for ext in archive_extensions)
                        )
                        is_program_file = (
                            lowered_name.endswith(program_extensions)
                            or decoded_path_lower.endswith(program_extensions)
                        )
                        is_archive_reference = (
                            any(lowered_name.endswith(ext) for ext in archive_extensions)
                            or any(decoded_path_lower.endswith(ext) for ext in archive_extensions)
                        )
                        is_web_url = bool(reference_url and safe_url.scheme in ("http", "https"))
                        is_source_page = is_web_url and (
                            "/details/" in safe_url.path.lower()
                            or not is_archive_reference and not is_program_file
                        )

                        link_html = "<em>URL not available in catalogue</em>"
                        if is_web_url and is_program_file:
                            if item_size is not None and 0 <= item_size <= max_reference_file_bytes:
                                link_html = (
                                    '<a href="' + html.escape(reference_url, quote=True)
                                    + '" target="_blank" rel="noopener noreferrer">'
                                    + html.escape(reference_url) + '</a>'
                                )
                                reference_type = "Individual program file"
                            else:
                                reference_type = "Program file"
                                link_html = "<em>Individual-file link hidden: file size is unknown or exceeds 10 MB.</em>"
                        elif is_web_url and is_archive_reference:
                            reference_type = "Archive or package"
                            link_html = (
                                '<a href="' + html.escape(reference_url, quote=True)
                                + '" target="_blank" rel="noopener noreferrer">'
                                + html.escape(reference_url) + '</a>'
                            )
                        elif is_web_url and is_nested_archive_path:
                            reference_type = "File inside archive"
                            link_html = "<em>Link hidden: the referenced file is not an individual program file.</em>"
                        elif is_source_page:
                            reference_type = "Source information page"
                            link_html = (
                                '<a href="' + html.escape(reference_url, quote=True)
                                + '" target="_blank" rel="noopener noreferrer">'
                                + html.escape(reference_url) + '</a>'
                            )
                        elif is_web_url:
                            reference_type = "Source page or other reference"
                            link_html = (
                                '<a href="' + html.escape(reference_url, quote=True)
                                + '" target="_blank" rel="noopener noreferrer">'
                                + html.escape(reference_url) + '</a>'
                            )
                        else:
                            reference_type = "Reference"

                        # A source page starts a new group. Do not display it as
                        # a loose file entry; show it as the group's linked heading.
                        if is_source_page:
                            title = reference_name
                            current_group = {"title": title, "source_url": reference_url, "entries": []}
                            source_groups.append(current_group)
                            current_archive = None
                            top_archive = None
                            continue

                        entry = {"name": reference_name, "type": reference_type,
                                 "link": link_html, "archive": is_archive_reference,
                                 "is_nested_path": is_nested_archive_path}
                        if is_archive_reference:
                            # A path such as Coll/foo.zip is nested inside the
                            # collection archive. Multiple such packages are siblings
                            # under that collection; their following files nest below
                            # the most recently listed package.
                            entry["nested_archive"] = "/" in unquote(reference_name).replace("\\", "/")
                            if entry["nested_archive"] and top_archive is not None:
                                top_archive.setdefault("children", []).append(entry)
                            else:
                                current_group["entries"].append(entry)
                                top_archive = entry
                            current_archive = entry
                        else:
                            if current_archive is not None:
                                current_archive.setdefault("children", []).append(entry)
                            else:
                                current_group["entries"].append(entry)

                    def render_reference(entry):
                        label = '<strong>' + html.escape(entry["type"]) + '</strong><br>' + html.escape(entry["name"])
                        body = label + '<br>' + entry["link"]
                        children = entry.get("children", [])
                        if children:
                            body += '<ul>' + ''.join('<li>' + render_reference(child) + '</li>' for child in children) + '</ul>'
                        return body

                    group_html = []
                    for group in source_groups:
                        if not group["entries"] and not group["source_url"]:
                            continue
                        title = html.escape(group["title"])
                        if group["source_url"]:
                            title = '<a href="' + html.escape(group["source_url"], quote=True) + '" target="_blank" rel="noopener noreferrer">' + title + '</a>'
                        entries_html = ''.join('<li>' + render_reference(entry) + '</li>' for entry in group["entries"])
                        group_html.append('<li><strong>Source: </strong>' + title + (('<ul>' + entries_html + '</ul>') if entries_html else '') + '</li>')

                    rows.append(
                        '<details><summary>Sources and archive paths (downloads may exceed 10MB, particularly ISOs); aggregated references</summary><ul>'
                        + ''.join(group_html)
                        + '</ul><small>Archive links are shown when a URL is available; downloads may exceed 10MB (particularly ISOs). Individual program-file links are shown only when the catalogue reports a size of 10 MB or less.</small></details>'
                    )

            if not rows:
                rows.append(
                    "<p>No files found.</p>"
                )

            page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{name}</title>
</head>
<body>

<h1>{name}</h1>

<p>
Platform: {html.escape(platforms)}<br>
Runtime: {html.escape(runtimes)}<br>
Language: {html.escape(languages)}
</p>

<hr>

<h2>FILES</h2>

{chr(10).join(rows)}

<hr>

<p>
<a href="/psionsoftware">BACK TO SOFTWARE</a>
</p>

<p>
<a href="/">BACK TO SIDECAR</a>
</p>

</body>
</html>
"""

            data = page.encode("utf-8")

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.send_header(
                "Cache-Control",
                "no-store"
            )
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:

            message = (
                "<html><body>"
                "<h1>Psion Software error</h1>"
                "<p>"
                "Could not load the program information."
                "</p>"
                "<p>"
                "<a href='/psionsoftware'>"
                "Back to Psion Software"
                "</a>"
                "</p>"
                "</body></html>"
            )

            data = message.encode("utf-8")

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(data))
            )
            self.end_headers()
            self.wfile.write(data)

    def handle_psiondownload(self, request_path):

        parsed = urlparse(request_path)

        query = parse_qs(
            parsed.query,
            keep_blank_values=True
        )

        program_id = query.get(
            "id",
            [""]
        )[0]

        hash_prefix = query.get(
            "h",
            [""]
        )[0]

        if not program_id:
            self.send_error(
                400,
                "Missing program ID"
            )
            return

        if not hash_prefix:
            self.send_error(
                400,
                "Missing file hash"
            )
            return

        try:

            with open(
                BASE_DIR / "software_index.json",
                "r",
                encoding="utf-8"
            ) as f:
                programs = json.load(f)

            program = None

            for item in programs:

                if item.get("id", "") == program_id:
                    program = item
                    break

            if program is None:
                self.send_error(
                    404,
                    "Program not found"
                )
                return

            is_package = (
                parsed.path.lower().endswith("/package.zip")
            )

            download_url = None
            filename = None
            output_filename = None

            candidates = []

            archive_extensions = (
                ".zip", ".iso", ".tar", ".7z", ".rar"
            )

            for version in program.get("versions", []):
                for variant in version.get("variants", []):
                    for item in variant.get("items", []):
                        item_hash = item.get("sha256", "")

                        if not item_hash or not item_hash.startswith(hash_prefix):
                            continue

                        if item.get("kind") not in ("installer", "standalone"):
                            continue

                        item_filename = item.get("filename", "")

                        references = item.get("references", item.get("reference", []))

                        if is_package:
                            # Preserve existing behaviour: do not offer a package download
                            # when this item has an SIS installer reference.
                            has_sis = any(
                                ref.get("url")
                                and urlparse(ref["url"]).path.lower().endswith(".sis")
                                for ref in references
                            )

                            if has_sis:
                                continue

                            selected_package_reference = _find_package_archive(
                                item_filename,
                                references
                            )

                            if selected_package_reference:
                                download_url = selected_package_reference.get("url")

                                if download_url:
                                    from urllib.parse import unquote_plus

                                    selected_name = unquote_plus(
                                        str(
                                            selected_package_reference.get("name", "")
                                            or urlparse(download_url).path.rsplit("/", 1)[-1]
                                        )
                                    ).replace("\\", "/")

                                    filename = selected_name.rsplit("/", 1)[-1]
                                    output_filename = filename

                            if download_url:
                                break

                            continue

                        # Installer downloads: SIS can be inside a parent
                        # archive; APP/OPA must have a direct reference.
                        for reference in references:
                            reference_url = reference.get("url")

                            if not reference_url:
                                continue

                            reference_path = urlparse(
                                reference_url
                            ).path

                            lower_path = reference_path.lower()

                            if not lower_path.endswith((".sis", ".app", ".opa")):
                                continue

                            path_parts = reference_path.split("/")

                            has_archive_parent = any(
                                part.lower().endswith(archive_extensions)
                                for part in path_parts[:-1]
                            )

                            # Archive.org can serve individual files from
                            # inside ZIP/ISO collections via nested-file URLs.
                            archive_host = (
                                urlparse(reference_url).hostname or ""
                            ).lower()

                            archive_org_nested_file = (
                                has_archive_parent
                                and (
                                    archive_host == "archive.org"
                                    or archive_host.endswith(".archive.org")
                                )
                                and any(
                                    part.lower().endswith((".zip", ".iso"))
                                    for part in path_parts[:-1]
                                )
                            )

                            # Permit standalone installers, including files
                            # individually referenced inside Archive.org
                            # ZIP/ISO collections.
                            if (
                                has_archive_parent
                                and not archive_org_nested_file
                            ):
                                continue

                            candidate_filename = (
                                reference.get("name", "")
                                or item_filename
                                or path_parts[-1]
                            ).replace("\\", "/").rsplit("/", 1)[-1]

                            candidates.append(
                                (candidate_filename, reference_url)
                            )

            if not is_package and candidates:
                # Prefer SIS installers over APP/OPA files.
                candidates.sort(
                    key=lambda candidate: (
                        0 if candidate[0].lower().endswith(".sis") else 1
                    )
                )

                filename, download_url = candidates[0]

            if not download_url:
                self.send_error(
                    404,
                    "Download not found"
                )
                return

            if not is_package:
                output_filename = filename[:-4] + ".bin"

            print(
                "Psion file download:",
                filename
            )

            print(
                "Source:",
                download_url
            )

            req = Request(
                download_url,
                headers={
                    "User-Agent":
                        "Mozilla/5.0 (Windows NT 10.0; "
                        "Win64; x64) "
                        "AppleWebKit/537.36 "
                        "Chrome/154.0.0.0 "
                        "Safari/537.36"
                }
            )

            with urlopen(
                req,
                timeout=60
            ) as response:

                data = response.read()

            print(
                "Downloaded:",
                len(data),
                "bytes"
            )

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/octet-stream"
            )

            self.send_header(
                "Content-Disposition",
                'attachment; filename="'
                + output_filename
                + '"'
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.send_header(
                "Cache-Control",
                "no-store"
            )

            self.end_headers()

            self.wfile.write(data)

        except Exception as e:

            print(
                "Package download error:" if is_package
                else "SIS download error:",
                repr(e)
            )


            message = (
                "<html><body>"
                "<h1>Download error</h1>"
                "<p>Could not download the SIS file.</p>"
                "<p><a href='/'>Back to Sidecar</a></p>"
                "</body></html>"
            )

            data = message.encode(
                "utf-8"
            )

            self.send_response(502)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()

            self.wfile.write(data)

    def handle_rmr(self, query):
        """Convert a Guardian crossword to RMR format and serve it."""
        import re

        filename = query.get("file", [""])[0].strip()

        # Be tolerant of a stale archive page that links an already-converted
        # file as an RMR input. Redirect to the existing file instead of
        # rejecting it as an invalid original crossword filename.
        if re.fullmatch(r"(?:Quick|Cryptic)_\d+_converted\.txt", filename):
            output_path = ROOT / filename
            if output_path.is_file():
                self.send_response(302)
                self.send_header("Location", "/" + quote(output_path.name))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
            else:
                self.send_error(404, "Converted crossword not found")
            return

        if not re.fullmatch(r"(?:Quick|Cryptic)_\d+\.txt", filename):
            self.send_error(400, "Invalid crossword filename")
            return

        source_path = ROOT / filename
        if not source_path.is_file():
            self.send_error(404, "Original crossword not found")
            return

        output_path = ROOT / (source_path.stem + "_converted.txt")

        try:
            if (
                not output_path.exists()
                or output_path.stat().st_mtime < source_path.stat().st_mtime
            ):
                import sys
                sys.path.insert(0, str(ROOT.parent))
                from crossword_converter import convert_text

                source = source_path.read_text(
                    encoding="utf-8", errors="replace"
                )
                converted = convert_text(source)
                output_path.write_text(
                    converted, encoding="utf-8", newline="\r\n"
                )
        except Exception as exc:
            self.send_error(422, "RMR conversion failed: " + str(exc))
            return

        self.send_response(302)
        self.send_header("Location", "/" + quote(output_path.name))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def handle_request(self, query):
        import sys

        kind = query.get("kind", [""])[0].strip().lower()
        number_text = query.get("number", [""])[0].strip()

        if kind not in ("quick", "cryptic"):
            self.send_error(400, "Invalid crossword type")
            return

        try:
            number = int(number_text)
        except ValueError:
            self.send_error(400, "Invalid crossword number")
            return

        sys.path.insert(0, str(ROOT.parent))

        try:
            import guardian_pi

            latest = guardian_pi.get_latest_number(kind)

            if kind == "quick":
                guardian_pi.QUICK_MAX = latest
            else:
                guardian_pi.CRYPTIC_MAX = latest

            if kind == "quick":
                filename = "Quick_%d.txt" % number
            else:
                filename = "Cryptic_%d.txt" % number

            already_exists = (ROOT / filename).exists()

            if already_exists:
                success = True
            else:
                success = guardian_pi.download_one(
                    kind,
                    number,
                    str(ROOT)
                )

        except Exception as e:
            success = False

        if success:

            if already_exists:
                status_text = (
                    "Already on Pi - no download needed."
                )
            else:
                status_text = "Downloaded successfully."

            if kind == "quick":
                filename = "Quick_%d.txt" % number
            else:
                filename = "Cryptic_%d.txt" % number

            message = (
                "<html><head><title>Psion Sidecar</title></head>"
                "<body>"
                "<h1>Request complete</h1>"
                "<p>%s</p>"
                "<p><a href='/%s'>Save original crossword</a></p>"
                "<p><a href='/rmr?file=%s'>Download RMR version</a></p>"
                "<hr>"
                "<h2>GET ANOTHER CROSSWORD</h2>"
                "<form action='/request' method='get'>"
                "<p>Quick number (9093-17583): "
                "<input type='hidden' name='kind' value='quick'>"
                "<input type='text' name='number' size='8'>"
                "<input type='submit' value='GET'>"
                "</p>"
                "</form>"
                "<form action='/request' method='get'>"
                "<p>Cryptic number (21620-30109): "
                "<input type='hidden' name='kind' value='cryptic'>"
                "<input type='text' name='number' size='8'>"
                "<input type='submit' value='GET'>"
                "</p>"
                "</form>"
                "</body></html>"
            ) % (
                html.escape(status_text),
                html.escape(filename),
                html.escape(filename)
            )

        else:

            message = (
                "<html><head><title>Psion Sidecar</title></head>"
                "<body>"
                "<h1>Download failed</h1>"
                "<p>The requested crossword could not be downloaded.</p>"
                "<p><a href='/'>Back to Sidecar</a></p>"
                "</body></html>"
            )

        data = message.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Cache-Control",
            "no-store, no-cache, must-revalidate"
        )
        self.send_header(
            "Pragma",
            "no-cache"
        )
        self.send_header(
            "Expires",
            "0"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()
        self.wfile.write(data)


    def send_homepage(self):
        page = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Psion Sidecar</title>
</head>
<body>

<h1>PSION HOME</h1>

<hr>

<h2>RESOURCES</h2>

<p><a href="/psionsoftware">Psion Community Software</a></p>
<p><a href="/guardian-crossword">Download The Guardian crossword</a></p>

<h3>Useful hyperlinks</h3>
<ol>
<li><a href="http://68k.news/">68k.news</a> - news headlines for vintage computers</li>
<li><a href="http://frogfind.de/">FrogFind</a> - web search, pages simplified</li>
<li><a href="https://lite.duckduckgo.com/lite/">DuckDuckGo Lite</a> - search</li>
<li><a href="https://text.npr.org/">NPR text</a> and <a href="https://lite.cnn.com/">CNN lite</a></li>
<li><a href="https://en.m.wikipedia.org/">Wikipedia</a> (mobile pages)</li>
<li><a href="https://wiby.me/">wiby.me</a> - a search engine for simple pages</li>
</ol>

<hr>

<p><strong>Psion Sidecar</strong><br>Shredder61 - 2026</p>

</body>
</html>
"""
        data = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_guardian_crossword(self):
        import sys

        sys.path.insert(0, str(ROOT.parent))

        try:
            from guardian_pi import (
                get_latest_number,
                QUICK_MIN, QUICK_MAX,
                CRYPTIC_MIN, CRYPTIC_MAX,
            )

            latest_quick = get_latest_number("quick")
            latest_cryptic = get_latest_number("cryptic")

        except Exception:
            # Fall back to the archive ranges stored in guardian_pi.py
            QUICK_MIN, QUICK_MAX = 9093, 17583
            CRYPTIC_MIN, CRYPTIC_MAX = 21620, 30109
            latest_quick = None
            latest_cryptic = None

        quick_high = latest_quick or QUICK_MAX
        cryptic_high = latest_cryptic or CRYPTIC_MAX

        # Converted RMR files are outputs, not source crosswords.
        # Keep them out of the archive list so they do not get an
        # invalid second "RMR version" link.
        quick_files = sorted(
            (
                p for p in ROOT.glob("Quick_*.txt")
                if not p.stem.endswith("_converted")
            ),
            key=lambda p: p.name
        )

        cryptic_files = sorted(
            (
                p for p in ROOT.glob("Cryptic_*.txt")
                if not p.stem.endswith("_converted")
            ),
            key=lambda p: p.name
        )

        def link_for(filename):
            name = html.escape(filename.name)

            return (
                f'<li>{name} — '
                f'<a href="/{name}">Original</a> | '
                f'<a href="/rmr?file={name}">RMR version</a></li>'
            )

        rows = []

        rows.append("<h2>TODAY'S CROSSWORDS</h2>")

        if latest_quick:

            quick_name = (
                ROOT / f"Quick_{latest_quick}.txt"
            )

            if quick_name.exists():

                rows.append(
                    f'<p><strong>Quick {latest_quick}</strong> '
                    f'<a href="/{html.escape(quick_name.name)}">'
                    f'Solve crossword</a></p>'
                )

            else:

                rows.append(
                    f"<p><strong>Quick {latest_quick}</strong> "
                    f"— not downloaded yet</p>"
                )

        if latest_cryptic:

            cryptic_name = (
                ROOT / f"Cryptic_{latest_cryptic}.txt"
            )

            if cryptic_name.exists():

                rows.append(
                    f'<p><strong>Cryptic {latest_cryptic}</strong> '
                    f'<a href="/{html.escape(cryptic_name.name)}">'
                    f'Solve crossword</a></p>'
                )

            else:

                rows.append(
                    f"<p><strong>Cryptic {latest_cryptic}</strong> "
                    f"— not downloaded yet</p>"
                )

        rows.append("<hr>")

        rows.append("<h2>ARCHIVE</h2>")

        rows.append("<h3>QUICK</h3>")
        rows.append("<ul>")

        for f in reversed(quick_files):

            if latest_quick and f.name == (
                f"Quick_{latest_quick}.txt"
            ):
                continue

            rows.append(link_for(f))

        rows.append("</ul>")
        rows.append("<h3>CRYPTIC</h3>")
        rows.append("<ul>")

        for f in reversed(cryptic_files):

            if latest_cryptic and f.name == (
                f"Cryptic_{latest_cryptic}.txt"
            ):
                continue

            rows.append(link_for(f))

        rows.append("</ul>")

        page = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Psion Sidecar</title>
</head>

<body>

<h1>THE GUARDIAN CROSSWORDS</h1>

<p><a href="/">BACK TO PSION HOME</a></p>

<hr>

<h2>GET A CROSSWORD</h2>

<p>
<small>
(NB: Use Reload All in Psion menu to refresh list)
</small>
</p>

<form action="/request" method="get">

<p>
Quick number (range: {QUICK_MIN}-{quick_high}):<br>
<input type="hidden" name="kind" value="quick">
<input type="text" name="number" size="8">
<input type="submit" value="GET">
</p>

</form>

<form action="/request" method="get">

<p>
Cryptic number (range: {CRYPTIC_MIN}-{cryptic_high}):<br>
<input type="hidden" name="kind" value="cryptic">
<input type="text" name="number" size="8">
<input type="submit" value="GET">
</p>

</form>

<hr>

{chr(10).join(rows)}

<hr>

<p><a href="/">BACK TO PSION HOME</a></p>

<p>
<strong>Psion Sidecar</strong><br>
Shredder61 - 2026
</p>

</body>
</html>
"""

        data = page.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(data))
        )
        self.end_headers()
        self.wfile.write(data)


def main():

    print("Guardian Sidecar web server")
    print(f"Serving: {ROOT}")
    print(f"Port: {PORT}")

    server = ThreadingHTTPServer(
        (HOST, PORT),
        lambda *args, **kwargs:
            SidecarHandler(
                *args,
                directory=str(ROOT),
                **kwargs
            )
    )

    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nStopping.")

    finally:
        server.server_close()


if __name__ == "__main__":
    main()
