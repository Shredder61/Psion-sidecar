#!/usr/bin/env python
# Guardian Crossword Downloader
# Python 2.7 and Python 3 compatible.
#
# IDLE use:
#   Run the file with F5 and answer the two questions.
#
# Command-line use:
#   python guardian.py quick 15779
#   python guardian.py cryptic 30103
#
# The program downloads the Guardian accessible/text-only crossword page
# and saves the puzzle in a simple text format.

from __future__ import print_function

import os
import re
import sys

# Guardian online archive number ranges last checked 12 September 2026.
# Quick: No 9,093 through No 17,583
# Cryptic: No 21,620 through No 30,109
QUICK_MIN = 9093
QUICK_MAX = 17583
CRYPTIC_MIN = 21620
CRYPTIC_MAX = 30109

# Default output directory: a crosswords folder beside this script.
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crosswords")

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser


try:
    input_func = raw_input
except NameError:
    input_func = input


class GuardianParser(HTMLParser):

    def __init__(self):
        try:
            HTMLParser.__init__(self, convert_charrefs=True)
        except TypeError:
            HTMLParser.__init__(self)

        self.heading_level = None
        self.heading_text = []
        self.section = None
        self.solution_section = None
        self.item_text = []
        self.items = {
            "Blanks": [],
            "Across": [],
            "Down": [],
            "AcrossSolutions": [],
            "DownSolutions": []
        }
        self.in_li = False
        self.title = ""
        self.in_title = False

        # Guardian presents solutions in HTML tables.
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.table_cells = []
        self.cell_text = []

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
            text = clean_text("".join(self.cell_text))
            self.table_cells.append(text)
            self.in_cell = False
            self.cell_text = []

        if tag == "tr" and self.in_row:
            if self.solution_section and len(self.table_cells) >= 3:
                start_position = self.table_cells[0]
                solution = self.table_cells[2]

                # Ignore the table heading row.
                if (start_position.lower() != "starting position" and
                        solution.lower() != "solution"):
                    if start_position and solution:
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
            if text:
                self.items[self.section].append(text)
            self.in_li = False
            self.item_text = []

        if tag in ("h2", "h3", "h4") and self.heading_level == tag:
            heading = clean_text("".join(self.heading_text))

            if heading in ("Blanks", "Across", "Down"):
                self.section = heading
                self.solution_section = None
            elif heading == "Across solutions":
                self.section = None
                self.solution_section = "AcrossSolutions"
            elif heading == "Down solutions":
                self.section = None
                self.solution_section = "DownSolutions"
            elif heading.startswith("Solutions"):
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

    def handle_entityref(self, name):
        value = "&" + name + ";"

        if self.in_li:
            self.item_text.append(value)

        if self.heading_level is not None:
            self.heading_text.append(value)

        if self.in_title:
            self.title += value

        if self.in_cell:
            self.cell_text.append(value)

    def handle_charref(self, name):
        value = "&#" + name + ";"

        if self.in_li:
            self.item_text.append(value)

        if self.heading_level is not None:
            self.heading_text.append(value)

        if self.in_title:
            self.title += value

        if self.in_cell:
            self.cell_text.append(value)


def clean_text(text):
    try:
        import HTMLParser as OldHTMLParser
        text = OldHTMLParser.HTMLParser().unescape(text)
    except Exception:
        try:
            from html import unescape
            text = unescape(text)
        except Exception:
            pass

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def psion_safe_text(text):
    """Convert Guardian Unicode punctuation to plain ASCII for the Psion."""
    replacements = {
        u"\u2014": u"-",      # em dash
        u"\u2013": u"-",      # en dash
        u"\u2012": u"-",      # figure dash
        u"\u2010": u"-",      # hyphen
        u"\u2011": u"-",      # non-breaking hyphen
        u"\u2018": u"'",      # left single quote
        u"\u2019": u"'",      # right single quote
        u"\u201a": u"'",      # single low-9 quote
        u"\u201c": u'"',      # left double quote
        u"\u201d": u'"',      # right double quote
        u"\u201e": u'"',      # double low-9 quote
        u"\u2026": u"...",    # ellipsis
        u"\u00a0": u" ",      # non-breaking space
        u"\u00ad": u"",       # soft hyphen
        u"\u2022": u"*",      # bullet
        u"\u00d7": u"x",      # multiplication sign
        u"\u00b7": u".",      # middle dot
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Decompose accented Latin characters where possible, then keep ASCII only.
    try:
        import unicodedata
        text = unicodedata.normalize("NFKD", text)
    except Exception:
        pass

    try:
        return text.encode("ascii", "ignore").decode("ascii")
    except AttributeError:
        return text.encode("ascii", "ignore")


def download(url):
    request = Request(url, headers={
        "User-Agent":
            "Mozilla/5.0 (Guardian crossword downloader; Psion project)"
    })

    response = urlopen(request, timeout=30)
    data = response.read()

    try:
        return data.decode("utf-8")
    except AttributeError:
        return data
    except UnicodeDecodeError:
        return data.decode("utf-8", "replace")


def make_output(parser, kind, number):

    blanks = parser.items["Blanks"]
    across = parser.items["Across"]
    down = parser.items["Down"]
    across_solutions = parser.items["AcrossSolutions"]
    down_solutions = parser.items["DownSolutions"]

    line_count = 0

    for item in blanks:
        if re.match(r"^Line\s+\d+\s*:", item, re.I):
            line_count += 1

    if line_count == 0:
        raise RuntimeError("No Guardian grid lines were found.")

    expected = 13 if kind == "quick" else 15

    if line_count != expected:
        raise RuntimeError(
            "Expected a %d-line %s grid, but found %d lines."
            % (expected, kind.capitalize(), line_count)
        )

    out = []

    out.append("Blanks")
    out.append("")
    out.extend(blanks)

    out.append("")
    out.append("Across")
    out.append("")
    out.extend(across)

    out.append("")
    out.append("Down")
    out.append("")
    out.extend(down)

    out.append("")
    out.append("Solutions")
    out.append("")
    out.append("Across solutions")
    out.extend(across_solutions)

    out.append("")
    out.append("Down solutions")
    out.extend(down_solutions)

    return "\n".join(out)



def validate_number(kind, number):
    """Check that the selected crossword number belongs to this series."""
    n = int(number)
    if kind == "quick":
        low, high = QUICK_MIN, QUICK_MAX
        label = "Quick"
    else:
        low, high = CRYPTIC_MIN, CRYPTIC_MAX
        label = "Cryptic"

    if n < low or n > high:
        return (
            "%s crossword numbers in the current Guardian online archive "
            "range from %d to %d. You entered %d."
            % (label, low, high, n)
        )
    return None


def download_one(kind, number, output_dir):
    """Download and save one crossword. Return True on success."""
    error = validate_number(kind, number)
    if error:
        print("ERROR: " + error)
        return False

    url = ("https://www.theguardian.com/crosswords/accessible/" "%s/%s" % (kind, number))
    print("\nDownloading:")
    print(url)
    try:
        html = download(url)
    except Exception as e:
        # Missing historical puzzles are normal gaps in the Guardian archive.
        # Record a 404 as NOT AVAILABLE and continue with the next puzzle.
        if getattr(e, "code", None) == 404:
            print(
                "NOT AVAILABLE: Crossword %d is not present in the Guardian online archive."
                % number
            )
            return False
        print("ERROR: Could not download crossword.")
        print(str(e))
        return False
    parser = GuardianParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as e:
        print("ERROR: Could not parse Guardian page.")
        print(str(e))
        return False
    try:
        text = make_output(parser, kind, number)
        text = psion_safe_text(text)
    except Exception as e:
        print("ERROR: " + str(e))
        return False
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError:
            if not os.path.isdir(output_dir):
                print("ERROR: Could not create output directory.")
                return False
    filename = "Quick_%s.txt" % number if kind == "quick" else "Cryptic_%s.txt" % number
    path = os.path.join(output_dir, filename)
    if os.path.exists(path):
        print("Already exists - skipped:", path)
        return True
    try:
        with open(path, "wb") as f:
            try:
                f.write(text.encode("utf-8"))
            except AttributeError:
                f.write(text)
    except Exception as e:
        print("ERROR: Could not save output.")
        print(str(e))
        return False
    print("Downloaded successfully.")
    print("Grid lines:", len(parser.items["Blanks"]))
    print("Across clues:", len(parser.items["Across"]))
    print("Down clues:", len(parser.items["Down"]))
    print("Across solutions:", len(parser.items["AcrossSolutions"]))
    print("Down solutions:", len(parser.items["DownSolutions"]))
    print("Saved:", os.path.abspath(path))
    return True


def get_kind():
    while True:
        kind = input_func("Crossword type (quick/cryptic) [Quick 9093-17583 / Cryptic 21620-30109]: ").strip().lower()
        if kind in ("quick", "cryptic"):
            return kind
        print("Please enter quick or cryptic.")


def get_number(prompt):
    while True:
        number = input_func(prompt).strip()
        if re.match(r"^\d+$", number):
            return number
        print("Please enter a crossword number.")

def get_latest_number(kind):
    import re
    import urllib.request

    url = "https://www.theguardian.com/crosswords/series/" + kind

    print("Checking Guardian for latest %s crossword..." % kind)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    data = urllib.request.urlopen(req, timeout=20).read()
    text = data.decode("utf-8", "ignore")

    if kind == "quick":
        pattern = r"Quick crossword No\s*([0-9,]+)"
    else:
        pattern = r"Cryptic crossword No\s*([0-9,]+)"

    match = re.search(pattern, text)

    if not match:
        raise RuntimeError(
            "Could not find the latest %s crossword number." % kind
        )

    return int(match.group(1).replace(",", ""))



def main():
    while True:
        print("")
        print("GUARDIAN CROSSWORD DOWNLOADER")
        print("")
        print("1 = Download one crossword")
        print("2 = Download a batch")
        print("3 = Download today's crossword")
        print("4 = Exit")
        print("")

        choice = input("Select: ").strip()

        if choice == "1":
            # Ask for the crossword type first, then display only that type's range.
            kind = input("Crossword type (quick/cryptic): ").strip().lower()

            if kind not in ("quick", "cryptic"):
                print("Please enter quick or cryptic.")
                continue

            if kind == "quick":
                low, high = QUICK_MIN, QUICK_MAX
                label = "Quick"
            else:
                low, high = CRYPTIC_MIN, CRYPTIC_MAX
                label = "Cryptic"

            print("%s crossword number range: %d to %d." % (label, low, high))
            number_text = input("Crossword number: ").strip()
            try:
                number = int(number_text)
            except ValueError:
                print("Please enter a valid crossword number.")
                continue

            output_dir = input(
                "Output directory (enter the full path, including a new directory if you want one; Enter for default which is to create/populate a crossword folder in the same folder as the program): "
            ).strip()

            if not output_dir:
                output_dir = DEFAULT_OUTPUT_DIR

            download_one(kind, number, output_dir)

        elif choice == "2":
            # Ask for the crossword type first, then display only that type's range.
            kind = input("Crossword type (quick/cryptic): ").strip().lower()

            if kind not in ("quick", "cryptic"):
                print("Please enter quick or cryptic.")
                continue

            if kind == "quick":
                low, high = QUICK_MIN, QUICK_MAX
                label = "Quick"
            else:
                low, high = CRYPTIC_MIN, CRYPTIC_MAX
                label = "Cryptic"

            print("%s crossword number range: %d to %d." % (label, low, high))
            first_text = input("First crossword number: ").strip()
            count_text = input("Number to download: ").strip()

            try:
                first = int(first_text)
                count = int(count_text)
            except ValueError:
                print("Please enter valid numbers.")
                continue

            if count < 1:
                print("Number to download must be at least 1.")
                continue

            last = first + count - 1

            if first < low or last > high:
                print(
                    "\nERROR: %s batch would run from %d to %d, "
                    "but the current archive range is %d to %d."
                    % (label, first, last, low, high)
                )
                continue

            output_dir = input(
                "Output directory (enter the full path, including a new directory if you want one; Enter for default which is to create/populate a crossword folder in the same folder as the program): "
            ).strip()

            if not output_dir:
                output_dir = DEFAULT_OUTPUT_DIR

            for number in range(first, last + 1):
                download_one(kind, number, output_dir)

        elif choice == "3":
            kind = input(
                "Crossword type (quick/cryptic): "
            ).strip().lower()
        
            if kind not in ("quick", "cryptic"):
                print("Please enter quick or cryptic.")
                continue
        
            try:
                number = get_latest_number(kind)
            except Exception as e:
                print("ERROR:", e)
                continue
        
            print(
                "Latest %s crossword is %d." %
                (kind.capitalize(), number)
            )
            if kind == "quick":
                globals()["QUICK_MAX"] = number
            else:
                globals()["CRYPTIC_MAX"] = number
        
            output_dir = DEFAULT_OUTPUT_DIR
        
            download_one(kind, number, output_dir)
        
        elif choice == "4":
            print("Exiting.")
            break
        
        else:
            print("Please select 1, 2, 3 or 4.")


if __name__ == "__main__":

    sys.exit(main())
