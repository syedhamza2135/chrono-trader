"""Wikipedia's S&P 500 pages: the current list (with CIKs), the change log, and old revisions of the list.

The fja05680/sp500 membership file is compiled from these pages and stops at its last update. The change
log extends it to today, and monthly revisions of the list give CIKs for companies that have since left.
Raw responses are cached under DATA_DIR/membership/wikipedia/ and never fetched twice.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

from .settings import DATA_DIR

CACHE = DATA_DIR / "membership" / "wikipedia"
API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "chrono-trader research project"}
LIST = "List_of_S&P_500_companies"
HISTORY = "Historical_components_of_the_S&P_500"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def _get(params):
    url = f"{API}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            if err.code != 429 and err.code < 500:
                raise
            wait = err.headers.get("Retry-After", "")
            time.sleep(int(wait) if wait.isdigit() else 15 * (attempt + 1))  # rate-limited: back off properly
        except OSError:
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"Wikipedia request failed: {params.get('page') or params.get('titles')}")


def current(title, day):
    """The page as it stands, cached under the day it was fetched."""
    path = CACHE / f"{title}@{day}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get({"action": "parse", "page": title, "prop": "wikitext", "format": "json", "formatversion": "2"}))
    return json.loads(path.read_text(encoding="utf-8"))["parse"]["wikitext"]


def revision(title, day):
    """(revision timestamp, wikitext) of the revision in force at 00:00 UTC on `day`."""
    path = CACHE / "revisions" / f"{title}@{day}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_get({"action": "query", "prop": "revisions", "titles": title, "rvlimit": "1",
                               "rvstart": f"{day}T00:00:00Z", "rvdir": "older", "rvprop": "ids|timestamp|content",
                               "rvslots": "main", "format": "json", "formatversion": "2"}))
        time.sleep(1)  # be polite to the API
    rev = json.loads(path.read_text(encoding="utf-8"))["query"]["pages"][0]["revisions"][0]
    return rev["timestamp"], rev["slots"]["main"]["content"]


def _rows(table):
    """Cells of each row of a wikitable, whether a row puts cells on separate lines or joins them with ||."""
    rows = []
    for chunk in re.split(r"\n\|-[^\n]*", table)[1:]:
        cells = []
        for line in chunk.split("\n"):
            if cells and line[:1].isspace() and line.lstrip().startswith("||"):  # the row's cells go on, indented (TSCO in early 2015)
                cells += [c.strip() for c in re.split(r"\|\|", line.lstrip()[2:])]
                continue
            if line.startswith("|}") or line.startswith("!") or not line.startswith("|"):
                if cells and line and not line.startswith(("|", "!")):
                    cells[-1] += " " + line  # a cell that wrapped onto the next line
                continue
            cells += [c.strip() for c in re.split(r"\|\|", line.lstrip("|"))]
        if cells:
            rows.append(cells)
    return rows


def _table(wikitext, marker):
    at = wikitext.find(marker)
    start = wikitext.rfind("{|", 0, at) if at >= 0 else wikitext.find("{|")
    return wikitext[start:wikitext.find("\n|}", start)]


def _header(table):
    """Lower-case column names, from every header line (rows of data never start with !)."""
    cols = []
    for line in table.split("\n"):
        if line.startswith("!"):
            for cell in line[1:].split("!!"):
                cell = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", cell)  # a link becomes its text
                cols.append(cell.split("|")[-1].strip().lower())  # drop attributes like rowspan="2" |
    return cols


def _symbol(cell):
    m = re.search(r"\{\{\s*[A-Za-z]*\s*(?:symbol|link)\s*\|\s*([A-Za-z0-9.\-/]+)", cell, flags=re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"\b([A-Z][A-Z0-9.\-/]{0,6})\b", re.sub(r"<[^>]+>|\[\[[^\]]*\]\]", "", cell))
    return m.group(1) if m else ""


def _name(cell):
    cell = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", cell)
    m = re.search(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell)
    text = (m.group(2) or m.group(1)) if m else cell
    return re.sub(r"\s+", " ", re.sub(r"\{\{[^}]*\}\}|'''?", "", text)).strip()


def _date(cell):
    cell = re.sub(r"<[^>]+>", "", cell)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", cell)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", cell)
    if m and m.group(1).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", cell)
    if m and m.group(2).lower() in MONTHS:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)))
    return None


def constituents(wikitext):
    """[{symbol, security, cik, date_added}] from a revision of the list. CIK is a 10-digit string or ''."""
    table = _table(wikitext, "Central Index Key")
    cols = _header(table)
    idx = {k: next((i for i, c in enumerate(cols) if any(w in c for w in words)), None)
           for k, words in {"symbol": ("symbol",), "security": ("security",), "cik": ("cik", "central index"),
                            "added": ("added",)}.items()}
    out = []
    for cells in _rows(table):
        if len(cells) <= max(i for i in idx.values() if i is not None):
            continue
        sym = _symbol(cells[idx["symbol"]])
        cik = re.sub(r"\D", "", re.sub(r"<ref.*?</ref>|<ref[^>]*/>", "", cells[idx["cik"]])) if idx["cik"] is not None else ""
        if sym:
            out.append({"symbol": sym, "security": _name(cells[idx["security"]]), "cik": cik.zfill(10) if cik else "",
                        "date_added": _date(cells[idx["added"]]) if idx["added"] is not None else None})
    return out


def changes(wikitext):
    """[{date, added, added_name, removed, removed_name, reason}] from the change log, newest first."""
    out, last_date = [], None
    for cells in _rows(_table(wikitext, 'id="changes"')):
        when = _date(cells[0]) if cells else None
        if when is None and last_date is not None and len(cells) == 6:
            when, cells = last_date, [""] + cells  # date cell spanning several rows
        if when is None or len(cells) < 6:
            continue
        last_date = when
        out.append({"date": when, "added": _symbol(cells[1]) if cells[1] else "", "added_name": _name(cells[2]),
                    "removed": _symbol(cells[3]) if cells[3] else "", "removed_name": _name(cells[4]),
                    "reason": _name(re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", cells[5]))})
    return out


def today():
    return datetime.now().date().isoformat()
