
#!/usr/bin/env python3
"""Download Guardian Quick, Cryptic, Weekend and Prize crosswords as PUZ files.

The first three positional arguments to download_one() are retained for
compatibility with Sidecar:
    download_one(kind, number, output_dir)

Examples:
    py guardian_pi.py quick --latest
    py guardian_pi.py cryptic --latest
    py guardian_pi.py weekend --latest
    py guardian_pi.py prize --latest
    py guardian_pi.py prize 29554 --no-solutions
    py guardian_pi.py quick 16001 --output crosswords
"""

import argparse
import os
import re
import sys
import time
from html import unescape
from html.parser import HTMLParser
from xml.etree import ElementTree
from urllib.request import Request, urlopen


DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "crosswords"
)

# Configured historical archive lower bounds. The upper bound is refreshed
# from the Guardian RSS feed. Quick and Cryptic retain their established
# archive starts. Weekend 321 is the earliest entry verified in the Guardian
# archive and successfully downloaded/converted in a batch test. Prize 21628
# is the lowest Prize crossword identified by the user. Numbering is not
# necessarily consecutive; batch downloads test every number in the range.
SERIES = {
    "quick": {
        "label": "Quick",
        "slug": "quick",
        "height": 13,
        "minimum": 9093,
    },
    "cryptic": {
        "label": "Cryptic",
        "slug": "cryptic",
        "height": 15,
        "minimum": 21620,
    },

    "weekend": {
        "label": "Weekend",
        "slug": "weekend",
        "series_slug": "weekend-crossword",
        "height": 13,
        "minimum": 321,
    },

    "prize": {
        "label": "Prize",
        "slug": "prize",
        "height": 15,
        "minimum": 21628,
    },
}

# Compatibility constants used by older scripts.
QUICK_MIN = 9093
QUICK_MAX = 17583
CRYPTIC_MIN = 21620
CRYPTIC_MAX = 30109

USER_AGENT = "Mozilla/5.0 (compatible; Psion Sidecar crossword downloader)"


def clean_text(value):
    """Decode HTML entities and normalise whitespace."""
    return re.sub(r"\s+", " ", unescape(value or "")).strip()


def psion_safe_text(value):
    """Replace typographic punctuation and remove non-ASCII characters."""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2010": "-",
        "\u2011": "-", "\u2018": "'", "\u2019": "'", "\u201a": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2026": "...",
        "\u00a0": " ", "\u00ad": "", "\u2022": "*", "\u00d7": "x",
        "\u00b7": ".",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    try:
        import unicodedata
        value = unicodedata.normalize("NFKD", value)
    except Exception:
        pass

    return value.encode("ascii", "ignore").decode("ascii")


class GuardianParser(HTMLParser):
    """Extract the accessible crossword's grid, clues and solution tables."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading_level = None
        self.heading_text = []
        self.section = None
        self.solution_section = None
        self.in_title = False
        self.title = ""

        self.in_li = False
        self.item_text = []

        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.table_cells = []
        self.cell_text = []

        self.items = {
            "Blanks": [],
            "Across": [],
            "Down": [],
            "AcrossSolutions": [],
            "DownSolutions": [],
        }

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "title":
            self.in_title = True

        if tag in ("h2", "h3", "h4"):
            self.heading_level = tag
            self.heading_text = []

        if tag == "li" and self.section in self.items:
            self.in_li = True
            self.item_text = []

        if tag == "table":
            self.in_table = True

        if tag == "tr" and self.in_table:
            self.in_row = True
            self.table_cells = []

        if tag in ("th", "td") and self.in_row:
            self.in_cell = True
            self.cell_text = []

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "title":
            self.in_title = False

        if tag in ("th", "td") and self.in_cell:
            self.table_cells.append(clean_text("".join(self.cell_text)))
            self.in_cell = False
            self.cell_text = []

        if tag == "tr" and self.in_row:
            if self.solution_section and len(self.table_cells) >= 3:
                start_position = self.table_cells[0]
                solution = self.table_cells[2]

                if (
                    start_position.lower() != "starting position"
                    and solution.lower() != "solution"
                    and start_position and solution
                ):
                    self.items[self.solution_section].append(
                        "(%s) %s" % (start_position, solution)
                    )

            self.in_row = False
            self.table_cells = []

        if tag == "table":
            self.in_table = False
            self.in_row = False
            self.in_cell = False

        if tag == "li" and self.in_li:
            text = clean_text("".join(self.item_text))
            # Some Guardian pages include an ordered-list number before
            # the actual clue, for example "1. (1A) Clue text".
            text = re.sub(r"^\s*\d+\.\s*", "", text)
            if text and self.section in self.items:
                self.items[self.section].append(text)
            self.in_li = False
            self.item_text = []

        if tag in ("h2", "h3", "h4") and self.heading_level == tag:
            heading = clean_text("".join(self.heading_text)).lower()

            if heading == "blanks":
                self.section = "Blanks"
                self.solution_section = None
            elif heading == "across":
                self.section = "Across"
                self.solution_section = None
            elif heading == "down":
                self.section = "Down"
                self.solution_section = None
            elif heading == "across solutions":
                self.section = None
                self.solution_section = "AcrossSolutions"
            elif heading == "down solutions":
                self.section = None
                self.solution_section = "DownSolutions"
            elif heading.startswith("solutions"):
                self.section = None
                self.solution_section = None

            self.heading_level = None
            self.heading_text = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.heading_level is not None:
            self.heading_text.append(data)
        if self.in_li:
            self.item_text.append(data)
        if self.in_cell:
            self.cell_text.append(data)


def download(url):
    """Download a Guardian page, retrying rate limits with backoff."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    max_429_retries = 5

    for attempt in range(max_429_retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                data = response.read()
            return data.decode("utf-8", "replace")
        except Exception as exc:
            if getattr(exc, "code", None) != 429 or attempt >= max_429_retries:
                raise

            # Respect Retry-After when supplied; otherwise use a steadily
            # increasing pause so a batch does not hammer the Guardian site.
            retry_after = None
            headers = getattr(exc, "headers", None)
            if headers is not None:
                retry_after = headers.get("Retry-After")

            try:
                delay = max(1, int(retry_after)) if retry_after else 30 * (2 ** attempt)
            except (TypeError, ValueError):
                delay = 30 * (2 ** attempt)

            delay = min(delay, 300)
            print(
                "Guardian rate limit (HTTP 429). "
                "Waiting %d seconds before retry %d of %d..."
                % (delay, attempt + 1, max_429_retries)
            )
            time.sleep(delay)

    raise RuntimeError("Guardian download failed after rate-limit retries.")


def validate_number(kind, number):
    kind = kind.lower()
    if kind not in SERIES:
        raise ValueError(
            "Unknown crossword type. Choose quick, cryptic, weekend or prize."
        )

    number = int(number)
    minimum = SERIES[kind]["minimum"]
    if number < minimum:
        raise ValueError(
            "%s crossword numbers must be at least %d."
            % (SERIES[kind]["label"], minimum)
        )
    return number


def make_source(parser, kind, number, no_solutions=False):
    """Build the plain-text source format expected by guardian_to_puz.py."""
    info = SERIES[kind]
    blanks = parser.items["Blanks"]
    across = parser.items["Across"]
    down = parser.items["Down"]

    line_count = sum(
        1 for item in blanks
        if re.match(r"^Line\s+\d+\s*:", item, re.I)
    )

    if line_count != info["height"]:
        raise RuntimeError(
            "Expected a %d-line %s grid, but found %d lines."
            % (info["height"], info["label"], line_count)
        )

    if not across or not down:
        raise RuntimeError("The page did not contain both clue lists.")

    output = ["Blanks", ""]
    output.extend(blanks)
    output.extend(["", "Across", ""])
    output.extend(across)
    output.extend(["", "Down", ""])
    output.extend(down)

    if not no_solutions:
        output.extend(["", "Solutions", "", "Across solutions"])
        output.extend(parser.items["AcrossSolutions"])
        output.extend(["", "Down solutions"])
        output.extend(parser.items["DownSolutions"])

    return psion_safe_text("\n".join(output))


class PuzzleNotFound(RuntimeError):
    """Raised when a requested puzzle number has no Guardian archive page."""


def fetch_source(kind, number, no_solutions=False, quiet=False):
    """Fetch and parse a Guardian crossword and determine solution status."""
    kind = kind.lower()
    number = validate_number(kind, number)
    slug = SERIES[kind]["slug"]

    url = "https://www.theguardian.com/crosswords/accessible/%s/%d" % (
        slug, number
    )

    if not quiet:
        print("\nDownloading:")
        print(url)

    try:
        page = download(url)
    except Exception as exc:
        if getattr(exc, "code", None) == 404:
            raise PuzzleNotFound(
                "%s crossword %d was not found in the Guardian archive."
                % (SERIES[kind]["label"], number)
            ) from exc
        raise RuntimeError("Could not download crossword: %s" % exc) from exc

    # Guardian explicitly identifies puzzles whose solutions are pending.
    solutions_pending = bool(re.search(
        r"Sorry,\s*solutions are not available",
        page,
        re.I
    ))

    parser = GuardianParser()

    try:
        parser.feed(page)
        parser.close()

        if not solutions_pending:
            across = parser.items["AcrossSolutions"]
            down = parser.items["DownSolutions"]

            # Do not silently produce an unsolved file if extraction failed.
            if not across or not down:
                raise RuntimeError(
                    "Guardian appears to have solutions available, "
                    "but the solution tables could not be extracted."
                )

        parser.solutions_available = not solutions_pending

        source = make_source(
            parser,
            kind,
            number,
            no_solutions=(no_solutions or solutions_pending)
        )

    except Exception as exc:
        raise RuntimeError(
            "Could not parse Guardian crossword: %s" % exc
        ) from exc

    return source, parser


def download_one(kind, number, output_dir, overwrite=False, no_solutions=False,
                 quiet_not_found=False, return_status=False):
    """Download one puzzle.

    The original boolean return is retained by default for Sidecar compatibility.
    Batch callers may request a status string and suppress expected 404 messages.
    """
    kind = kind.lower()

    if kind not in SERIES:
        print("ERROR: Unknown crossword type:", kind)
        return False

    try:
        number = validate_number(kind, number)
        os.makedirs(output_dir, exist_ok=True)

        # Fetch first, so an existing pending puzzle can be upgraded.
        source, parser = fetch_source(
            kind,
            number,
            no_solutions=no_solutions,
            quiet=quiet_not_found
        )

        if no_solutions:
            suffix = "_no_solutions"
        elif not parser.solutions_available:
            suffix = "_pending"
        else:
            suffix = ""

        filename = "%s_%d%s.puz" % (
            SERIES[kind]["label"],
            number,
            suffix
        )

        path = os.path.join(output_dir, filename)

        if os.path.exists(path) and not overwrite:
            print("Already exists - skipped:", path)

            # A solved file already exists, so an obsolete pending copy
            # can safely be removed.
            if parser.solutions_available and not no_solutions:
                pending_path = os.path.join(
                    output_dir,
                    "%s_%d_pending.puz" % (
                        SERIES[kind]["label"], number
                    )
                )
                if os.path.exists(pending_path):
                    os.remove(pending_path)
                    print("Removed obsolete pending file:", pending_path)

            return "skipped" if return_status else True

        from guardian_to_puz import convert_source

        puzzle = convert_source(
            source,
            path,
            title="Guardian %s %d" % (
                SERIES[kind]["label"], number
            )
        )

        # Once the solved version has been successfully written,
        # remove the earlier pending version.
        if parser.solutions_available and not no_solutions:
            pending_path = os.path.join(
                output_dir,
                "%s_%d_pending.puz" % (
                    SERIES[kind]["label"], number
                )
            )

            if os.path.exists(pending_path):
                os.remove(pending_path)
                print("Removed obsolete pending file:", pending_path)

    except PuzzleNotFound as exc:
        if not quiet_not_found:
            print("ERROR:", str(exc))
        return "not_found" if return_status else False
    except Exception as exc:
        print("ERROR:", str(exc))
        return "failed" if return_status else False

    print("Downloaded and converted successfully.")
    print("Grid:", puzzle["width"], "x", puzzle["height"])
    print("Across clues:", len(puzzle["across_clues"]))
    print("Down clues:", len(puzzle["down_clues"]))

    if no_solutions:
        print("Solutions: deliberately omitted")
    elif parser.solutions_available:
        print("Solutions: downloaded")
    else:
        print("Solutions: not yet published by Guardian")

    print("Saved:", os.path.abspath(path))
    return "downloaded" if return_status else True


def get_available_numbers(kind):
    """Return puzzle numbers listed in the Guardian series RSS feed.

    The RSS feed is a recent-puzzles index (currently about 20 entries),
    not a complete historical archive. Numbers are returned newest first.
    """
    kind = kind.lower()
    if kind not in SERIES:
        raise ValueError("Unknown crossword type: " + kind)

    info = SERIES[kind]
    series_slug = info.get("series_slug", info["slug"])
    url = "https://www.theguardian.com/crosswords/series/%s/rss" % series_slug
    xml_data = download(url)

    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError as exc:
        raise RuntimeError(
            "Could not parse the Guardian %s RSS feed: %s"
            % (info["label"], exc)
        ) from exc

    numbers = []
    seen = set()
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""

        # Prefer the canonical puzzle URL; title is a fallback for feed
        # variants that do not include a standard link.
        match = re.search(
            r"/crosswords/%s/(\d+)(?:[/?#]|$)" % re.escape(info["slug"]),
            link,
            re.I,
        )
        if not match:
            label = re.escape(info["label"])
            match = re.search(
                r"%s\s+crossword\s+No\.?\s*([0-9,]+)" % label,
                clean_text(title),
                re.I,
            )

        if not match:
            continue

        number = int(match.group(1).replace(",", ""))
        if number < info["minimum"] or number in seen:
            continue
        seen.add(number)
        numbers.append(number)

    if not numbers:
        raise RuntimeError(
            "The Guardian %s RSS feed contained no recognisable puzzle entries."
            % info["label"]
        )

    return numbers


def get_archive_info(kind):
    """Return the configured full archive bounds and live RSS maximum.

    The minimum comes from SERIES[kind]["minimum"]. The maximum is refreshed
    from the first (newest) entry in the Guardian RSS feed. RSS itself only
    contains recent entries and is not used as the historical lower bound.
    """
    kind = kind.lower()
    if kind not in SERIES:
        raise ValueError("Unknown crossword type: " + kind)

    numbers = get_available_numbers(kind)
    ordered = sorted(numbers)
    differences = [b - a for a, b in zip(ordered, ordered[1:])]
    step = differences[0] if differences and len(set(differences)) == 1 else 1

    return {
        "kind": kind,
        "numbers": numbers,
        "minimum": SERIES[kind]["minimum"],
        "maximum": numbers[0],
        "latest": numbers[0],
        "oldest_listed": ordered[0],
        "newest_listed": ordered[-1],
        "count": len(numbers),
        "step": step,
    }


def get_latest_number(kind):
    """Return today's/latest published puzzle number using the RSS feed."""
    kind = kind.lower()
    if kind not in SERIES:
        raise ValueError("Unknown crossword type: " + kind)

    print("Checking Guardian RSS for today's %s crossword..." % SERIES[kind]["label"])
    return get_available_numbers(kind)[0]


def prompt_output_dir():
    value = input(
        "Output directory (Enter for the crosswords folder beside this program): "
    ).strip()
    return value or DEFAULT_OUTPUT_DIR


def choose_kind():
    while True:
        value = input(
            "Crossword type (quick/cryptic/weekend/prize): "
        ).strip().lower()
        if value in SERIES:
            return value
        print("Please enter quick, cryptic, weekend or prize.")


def run_batch(kind, first, count, output_dir, overwrite=False):
    if count < 1:
        print("Number to download must be at least 1.")
        return

    downloaded = skipped = failed = 0
    for number in range(first, first + count):
        suffix = ""
        filename = "%s_%d%s.puz" % (
            SERIES[kind]["label"], number, suffix
        )
        existed = os.path.isfile(os.path.join(output_dir, filename))

        ok = download_one(
            kind, number, output_dir, overwrite=overwrite
        )
        if not ok:
            failed += 1
        elif existed and not overwrite:
            skipped += 1
        else:
            downloaded += 1

    print("\nBATCH SUMMARY")
    print("Downloaded:", downloaded)
    print("Already existed (skipped):", skipped)
    print("Unavailable or failed:", failed)
    print("Total processed:", downloaded + skipped + failed)


def display_archive_information():
    """Display full configured archive bounds and the RSS-derived maximum."""
    print("\nGUARDIAN CROSSWORD ARCHIVE RANGES")
    print("(Archive minimum from program settings; maximum refreshed from Guardian RSS)\n")
    information = {}

    for kind, info in SERIES.items():
        try:
            details = get_archive_info(kind)
            information[kind] = details
            interval_note = " (every {})".format(details["step"]) if details["step"] > 1 else ""
            print(
                "{:<9} Archive: {:>6} - {:>6} | Today's: {:>6}{}".format(
                    info["label"], details["minimum"], details["maximum"],
                    details["latest"], interval_note,
                )
            )
        except Exception as exc:
            print("{:<9} archive range unavailable ({})".format(info["label"], exc))

    return information


def run_batch_range(kind, first, last, output_dir, overwrite=False,
                    archive_info=None):
    """Try every number in an inclusive range; skip Guardian 404 responses.

    No local archive list or assumed numbering interval is used. This ensures
    irregularly numbered puzzles are not missed. archive_info is retained for
    compatibility with the interactive menu.
    """
    kind = kind.lower()
    if kind not in SERIES:
        print("Unknown crossword type:", kind)
        return
    if first > last:
        print("The start number must not be greater than the end number.")
        return

    minimum = SERIES[kind]["minimum"]
    if first < minimum:
        print(
            "Start number is below the configured archive minimum of %d."
            % minimum
        )
        return

    print(
        "\nChecking every %s puzzle number from %d to %d. "
        "Numbers not present in Guardian will be skipped."
        % (SERIES[kind]["label"], first, last)
    )

    downloaded = skipped = unavailable = failed = 0
    for number in range(first, last + 1):
        status = download_one(
            kind,
            number,
            output_dir,
            overwrite=overwrite,
            quiet_not_found=True,
            return_status=True,
        )

        if status == "downloaded":
            downloaded += 1
        elif status == "skipped":
            skipped += 1
        elif status == "not_found":
            unavailable += 1
        else:
            failed += 1
            print("Failed to process %s crossword %d." % (
                SERIES[kind]["label"], number
            ))

        if number < last:
            time.sleep(2)

    print("\nBATCH SUMMARY")
    print("Detected %d downloadable crosswords." % (downloaded + skipped))
    print("Downloaded:", downloaded)
    print("Already existed (skipped):", skipped)
    if failed:
        print("Other failures:", failed)
    print("Numbers checked:", last - first + 1)


def interactive_menu():
    archive_information = display_archive_information()

    while True:
        print("\nGUARDIAN CROSSWORD DOWNLOADER")
        print("1 = Download one crossword")
        print("2 = Download a batch (start and end numbers)")
        print("3 = Download Today's crossword")
        print("4 = Refresh archive information")
        print("5 = Exit")

        choice = input("Select: ").strip()

        if choice == "1":
            kind = choose_kind()
            # Show the full configured archive span, using the RSS-refreshed
            # latest number already retrieved when the menu was displayed.
            details = archive_information.get(kind)
            if details:
                range_text = "{}-{}".format(
                    details["minimum"], details["maximum"]
                )
                interval_note = (
                    " (numbering interval {})".format(details["step"])
                    if details.get("step", 1) > 1 else ""
                )
                prompt = "Crossword number (archive range {}{}): ".format(
                    range_text, interval_note
                )
            else:
                minimum = SERIES[kind]["minimum"]
                prompt = (
                    "Crossword number (minimum {}; latest range unavailable): "
                    .format(minimum)
                )

            number_text = input(prompt).strip()
            if not number_text.isdigit():
                print("Please enter a valid crossword number.")
                continue
            download_one(kind, int(number_text), prompt_output_dir())

        elif choice == "2":
            kind = choose_kind()
            details = archive_information.get(kind)
            if details:
                range_text = "{}-{}".format(
                    details["minimum"], details["maximum"]
                )
            else:
                range_text = "minimum {}".format(SERIES[kind]["minimum"])

            first_text = input(
                "Start crossword number (range {}): ".format(range_text)
            ).strip()
            last_text = input(
                "End crossword number (range {}): ".format(range_text)
            ).strip()
            if not first_text.isdigit() or not last_text.isdigit():
                print("Please enter valid start and end numbers.")
                continue
            run_batch_range(
                kind, int(first_text), int(last_text), prompt_output_dir(),
                archive_info=archive_information.get(kind),
            )

        elif choice == "3":
            kind = choose_kind()
            try:
                number = get_latest_number(kind)
                print("Today's %s crossword is %d." % (
                    SERIES[kind]["label"], number
                ))
                download_one(kind, number, prompt_output_dir())
            except Exception as exc:
                print("ERROR:", exc)

        elif choice == "4":
            archive_information = display_archive_information()

        elif choice == "5":
            print("Exiting.")
            return 0

        else:
            print("Please select 1, 2, 3, 4 or 5.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Download Guardian crosswords as Across Lite PUZ files."
    )
    parser.add_argument(
        "kind", nargs="?",
        choices=sorted(SERIES),
        help="quick, cryptic, weekend or prize",
    )
    parser.add_argument("number", nargs="?", type=int)
    parser.add_argument("--latest", action="store_true",
                         help="download Today's/latest published puzzle")
    parser.add_argument("--no-solutions", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--menu", action="store_true")

    args = parser.parse_args(argv)

    if args.menu or (args.kind is None and args.number is None
                     and not args.latest):
        return interactive_menu()

    if args.kind is None:
        parser.error("Specify a crossword type.")

    if args.latest and args.number is not None:
        parser.error("Use either a crossword number or --latest, not both.")

    try:
        number = get_latest_number(args.kind) if args.latest else args.number
        if number is None:
            parser.error("Specify a crossword number or use --latest.")

        if args.latest:
            print("Today's %s crossword is %d." % (
                SERIES[args.kind]["label"], number
            ))

        success = download_one(
            args.kind,
            number,
            args.output,
            overwrite=args.overwrite,
            no_solutions=args.no_solutions,
        )
        return 0 if success else 1

    except Exception as exc:
        print("ERROR:", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
