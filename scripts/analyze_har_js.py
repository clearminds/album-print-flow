#!/usr/bin/env python3
"""
Analyze JavaScript and HTML in a Google Photos HAR to see how BatchExecute
and the anti-forgery token (at) are used.

Usage:
  python scripts/analyze_har_js.py [path/to/photos.google.com.har]

Writes a short report to stdout. HAR path defaults to
~/Downloads/photos.google.com.har.
"""

from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path


def get_response_text(entry: dict) -> str:
    content = entry.get("response", {}).get("content", {})
    text = content.get("text") or ""
    if content.get("encoding") == "base64":
        try:
            text = base64.b64decode(text).decode("utf-8", errors="replace")
        except Exception:
            pass
    return text


def main() -> int:
    har_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "photos.google.com.har"
    if not har_path.exists():
        print(f"HAR not found: {har_path}", file=sys.stderr)
        return 1

    with open(har_path) as f:
        har = json.load(f)

    entries = har["log"]["entries"]
    keywords = ["batchexecute", "eNG3nf", "yQelMe", "SNlM0e", "rpcids", "f.req", "f.sid"]

    # Which entries contain each keyword (record index and URL only)
    by_keyword: dict[str, list[tuple[int, str]]] = {k: [] for k in keywords}
    for i, entry in enumerate(entries):
        text = get_response_text(entry)
        if len(text) > 700_000:
            text = text[:700_000]
        url = (entry.get("request") or {}).get("url", "")[:70]
        for kw in keywords:
            if kw in text:
                by_keyword[kw].append((i, url))

    print("=== HAR JS/HTML analysis ===\n")
    print("Keyword occurrence (entry index, request URL):")
    for kw in keywords:
        hits = by_keyword[kw]
        print(f"  {kw}: {len(hits)} entries")
        for idx, url in hits[:5]:
            print(f"    {idx}  {url}")

    # Initial HTML (entry 0): at token key SNlM0e
    html = get_response_text(entries[0])
    normalized_html = html.replace('\\"', '"')
    snl = re.search(r'"SNlM0e"\s*:\s*"([^"]+)"', normalized_html)
    if snl:
        at_val = snl.group(1)
        print(f"\nHTML (entry 0): at token in SNlM0e = {at_val[:40]}...")
    else:
        print("\nHTML (entry 0): no SNlM0e key found")

    # PhotosUi JS (largest JS that has batchexecute): how URL and at are built
    photos_ui_entries = [i for i, _ in by_keyword["batchexecute"] if "PhotosUi" in (entries[i].get("request") or {}).get("url", "")]
    if photos_ui_entries:
        idx = photos_ui_entries[0]
        js = get_response_text(entries[idx])
        snippets = []
        for pattern, label in [
            (r"\.at\s*=\s*[^;]+", "at assignment"),
            (r"eptZe[^;`]{0,60}", "batchexecute path prefix"),
            (r"data/batchexecute[^`\"]{0,40}", "batchexecute path"),
            (r"yQelMe[^;]{0,40}", "yQelMe RPC"),
        ]:
            m = re.search(pattern, js)
            if m:
                snip = m.group(0).replace("\n", " ").strip()[:100]
                snippets.append(f"  {label}: {snip}")
        if snippets:
            print(f"\nPhotosUi JS (entry {idx}):")
            print("\n".join(snippets))

    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
