#!/usr/bin/env python3
"""Cross-check publications.md entries against Inspire and arXiv metadata."""

import argparse
import json
import re
import sys
import time
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen


INSPIRE_API = "https://inspirehep.net/api/literature/{}"
ARXIV_API = "http://export.arxiv.org/api/query?search_query=id:{}"


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def strip_html_breaks(text):
    return text.replace("<br/>", " ").replace("<br>", " ")


def normalize(text):
    # Lowercase, strip punctuation, collapse whitespace.
    text = text.lower()
    text = re.sub(r"[‐‑–—]", "-", text)
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_entries(md_text):
    entries = []
    current_year = None
    current = None

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n")
        if re.match(r"^\*\*20\d{2}\*\*$", line.strip()):
            current_year = line.strip().strip("*")
            continue
        if line.startswith("- "):
            if current:
                entries.append(current)
            current = {"year": current_year, "lines": [line]}
            continue
        if current:
            if not line.strip():
                entries.append(current)
                current = None
                continue
            current["lines"].append(line)

    if current:
        entries.append(current)
    return entries


def extract_fields(entry):
    text = strip_html_breaks(" ".join(entry["lines"]))
    text = re.sub(r"\s+", " ", text).strip()

    authors = None
    title = None
    link_text = None
    link_url = None

    bold = re.findall(r"\*\*(.+?)\*\*", text)
    if bold:
        authors = bold[0].strip()

    italics = re.findall(r"\*(?!\*)(.+?)(?<!\*)\*", text)
    if italics:
        title = italics[0].strip()

    link = re.search(r"\[([^\]]+)\]\(([^)]+)\)", text)
    if link:
        link_text = link.group(1).strip()
        link_url = link.group(2).strip()

    return {
        "year": entry["year"],
        "authors": authors,
        "title": title,
        "link_text": link_text,
        "link_url": link_url,
    }


def extract_inspire_id(url):
    if not url:
        return None
    m = re.search(r"inspirehep\.net/literature/(\d+)", url)
    if m:
        return m.group(1)
    return None


def extract_arxiv_id_from_text(text):
    if not text:
        return None
    m = re.search(r"(\d{4}\.\d{4,5}|[a-z-]+/\d{7})", text)
    return m.group(1) if m else None


def extract_arxiv_id_from_url(url):
    if not url:
        return None
    parsed = urlparse(url)
    if "arxiv.org" in parsed.netloc and parsed.path.startswith("/abs/"):
        return parsed.path.split("/abs/")[1]

    query = parse_qs(parsed.query)
    if "q" in query:
        raw = unquote(query["q"][0])
        m = re.search(r"arxiv:([\w./-]+)", raw, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def http_get_json(url, timeout):
    req = Request(url, headers={"User-Agent": "qgt-publications-check/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_text(url, timeout):
    req = Request(url, headers={"User-Agent": "qgt-publications-check/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_inspire(inspire_id, timeout):
    url = INSPIRE_API.format(inspire_id)
    data = http_get_json(url, timeout)
    meta = data.get("metadata", {})
    title = None
    if meta.get("titles"):
        title = meta["titles"][0].get("title")

    authors = []
    for author in meta.get("authors", []):
        full = author.get("full_name")
        if full:
            authors.append(full)

    arxiv_id = None
    if meta.get("arxiv_eprints"):
        arxiv_id = meta["arxiv_eprints"][0].get("value")

    return {
        "title": title,
        "authors": authors,
        "arxiv_id": arxiv_id,
    }


def fetch_arxiv(arxiv_id, timeout):
    url = ARXIV_API.format(arxiv_id)
    return http_get_text(url, timeout)


def first_author_last_name(authors_text):
    if not authors_text:
        return None
    first_part = re.split(r",| and ", authors_text)[0].strip()
    tokens = first_part.split()
    return tokens[-1].strip(".,") if tokens else None


def inspire_first_author_last_name(authors):
    if not authors:
        return None
    first = authors[0]
    # Inspire uses "Last, First".
    parts = [p.strip() for p in first.split(",")]
    if parts:
        return parts[0]
    return None


def compare_entry(entry, meta):
    issues = []
    if entry["title"] and meta["title"]:
        if normalize(entry["title"]) != normalize(meta["title"]):
            issues.append("title_mismatch")
    elif entry["title"] or meta["title"]:
        issues.append("title_missing")

    if entry.get("arxiv_id") and meta.get("arxiv_id"):
        if entry["arxiv_id"] != meta["arxiv_id"]:
            issues.append("arxiv_mismatch")

    entry_last = first_author_last_name(entry.get("authors"))
    meta_last = inspire_first_author_last_name(meta.get("authors"))
    if entry_last and meta_last:
        if normalize(entry_last) != normalize(meta_last):
            issues.append("first_author_mismatch")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Cross-check publications.md against Inspire/arXiv.")
    parser.add_argument("path", nargs="?", default="publications.md")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of entries to check")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    md_text = read_text(args.path)
    entries = [extract_fields(e) for e in parse_entries(md_text)]

    for i, entry in enumerate(entries, start=1):
        if args.limit and i > args.limit:
            break

        inspire_id = extract_inspire_id(entry.get("link_url"))
        arxiv_id = extract_arxiv_id_from_text(entry.get("link_text"))
        arxiv_id = arxiv_id or extract_arxiv_id_from_url(entry.get("link_url"))
        entry["inspire_id"] = inspire_id
        entry["arxiv_id"] = arxiv_id

        status = "OK"
        issues = []

        if inspire_id:
            meta = fetch_inspire(inspire_id, args.timeout)
            issues = compare_entry(entry, meta)
        else:
            meta = None
            issues = ["missing_inspire_id"]

        if issues:
            status = "DIFF"

        print(f"[{status}] {entry.get('year') or '????'} #{i}")
        print(f"  Title: {entry.get('title')}")
        print(f"  Link: {entry.get('link_url')}")
        if inspire_id:
            print(f"  Inspire ID: {inspire_id}")
        if arxiv_id:
            print(f"  arXiv ID: {arxiv_id}")
        if issues:
            print(f"  Issues: {', '.join(issues)}")
        print("")

        if args.sleep:
            time.sleep(args.sleep)

    return 0


if __name__ == "__main__":
    sys.exit(main())
