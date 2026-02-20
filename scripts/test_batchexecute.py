#!/usr/bin/env python3
"""
Standalone test script for Google Photos BatchExecute (sid/bl/at, eNG3nf, yQelMe).
Run against a real shared album URL to verify token extraction and response parsing.

Usage:
  python scripts/test_batchexecute.py "https://photos.google.com/share/AF1Qip..."
  python scripts/test_batchexecute.py   # uses ALBUM_URL env if set

Prints: tokens, user_id, base_url count, raw yQelMe response (and length),
        parsed date count + sample. No app or package install required.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("Need requests: pip install requests", file=sys.stderr)
    sys.exit(1)


def main() -> int:
    if len(sys.argv) > 1:
        album_url = sys.argv[1].strip()
    else:
        import os
        album_url = os.environ.get("ALBUM_URL", "").strip()
    if not album_url:
        print("Usage: python scripts/test_batchexecute.py <album_url>", file=sys.stderr)
        print("   or: ALBUM_URL=<url> python scripts/test_batchexecute.py", file=sys.stderr)
        return 1
    if not album_url.startswith("http"):
        album_url = "https://" + album_url

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    print("GET", album_url[:80], "...")
    try:
        resp = session.get(album_url, allow_redirects=True, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print("GET failed:", e, file=sys.stderr)
        return 1

    resolved_url = resp.url
    html = resp.text
    normalized = html.replace('\\"', '"')
    print("Resolved URL:", resolved_url[:90], "...")
    print("HTML length:", len(html))

    # Token extraction (same logic as google_photos_album_url_source)
    sid = None
    for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*"(-?\d{15,20})"', normalized):
        val = m.group(2)
        if val.lstrip("-").isdigit() and len(val) >= 15:
            sid = val
            break
    bl_m = re.search(r"boq_photosuiserver_[a-zA-Z0-9._]+", normalized)
    bl = bl_m.group(0) if bl_m else None
    at = None
    for m in re.finditer(
        r'"([A-Za-z0-9_]+)"\s*:\s*"([A-Za-z0-9_-]+:\d{13})"', normalized
    ):
        at = m.group(2)
        break
    user_id = None
    if sid:
        for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*"(\d{18,22})"', normalized):
            val = m.group(2)
            if val != sid.lstrip("-"):
                user_id = val
                break

    print("sid:", sid[:12] + "..." if sid and len(sid) > 12 else sid)
    print("bl:", bl)
    print("at:", (at[:30] + "..." if at and len(at) > 30 else at) or "(none)")
    print("user_id:", (user_id[:12] + "..." if user_id and len(user_id) > 12 else user_id) or "(none)")

    # Base URLs (same regex as _extract_media_bases)
    base_urls = []
    seen = set()
    for raw in re.findall(
        r"https://lh3\.googleusercontent\.com/pw/[^\"'\s)]+",
        normalized.replace("\\/", "/").replace("\\u003d", "=").replace("\\u0026", "&"),
    ):
        base = raw.split("=", 1)[0].strip()
        if base and base not in seen:
            seen.add(base)
            base_urls.append(base)
    print("base_urls:", len(base_urls))
    if base_urls:
        print("  first:", base_urls[0][:70], "...")

    if not sid or not bl:
        print("Missing sid or bl; cannot call BatchExecute.")
        return 0

    parsed = urllib.parse.urlparse(resolved_url)
    path = (parsed.path or "/").lstrip("/") or "/"
    if not path.startswith("/"):
        path = "/" + path
    base = "https://photos.google.com/_/PhotosUi/data/batchexecute"

    # eNG3nf first when we have user_id
    if user_id:
        params = {
            "rpcids": "eNG3nf",
            "source-path": path,
            "f.sid": sid,
            "bl": bl,
            "hl": "en",
            "soc-app": "165",
            "soc-platform": "1",
            "soc-device": "1",
            "rt": "c",
        }
        url_eng = f"{base}?{urllib.parse.urlencode(params)}"
        inner = (
            '[[[[null,"'
            + user_id
            + '"]],[null,[],[null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,null,[],[]],[null,null,[[]]],null,null,null,null,null,null,null,null,null,null,null,[]]]]'
        )
        body_eng = {"f.req": json.dumps([[["eNG3nf", inner, None, "generic"]]])}
        if at:
            body_eng["at"] = at
        print("\nPOST eNG3nf ...")
        try:
            r_eng = session.post(
                url_eng,
                data=body_eng,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": session.headers["User-Agent"],
                },
                timeout=30,
            )
            print("  status:", r_eng.status_code, "len:", len(r_eng.text))
            if not r_eng.ok:
                print("  body start:", r_eng.text[:300])
        except requests.RequestException as e:
            print("  error:", e)

    # yQelMe
    params = {
        "rpcids": "yQelMe",
        "source-path": path,
        "f.sid": sid,
        "bl": bl,
        "hl": "en",
        "soc-app": "165",
        "soc-platform": "1",
        "soc-device": "1",
        "rt": "c",
    }
    url_yq = f"{base}?{urllib.parse.urlencode(params)}"
    body_yq = {
        "f.req": json.dumps([[["yQelMe", "[null,null,null,[[1,null,1]]]", None, "generic"]]]),
    }
    if at:
        body_yq["at"] = at
    print("\nPOST yQelMe ...")
    try:
        r_yq = session.post(
            url_yq,
            data=body_yq,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": session.headers["User-Agent"],
            },
            timeout=30,
        )
    except requests.RequestException as e:
        print("  error:", e)
        return 1

    print("  status:", r_yq.status_code)
    batch_text = r_yq.text
    print("  response length:", len(batch_text))
    print("  raw response (full):")
    print("  ", repr(batch_text))
    print()

    # Parse (same as _parse_batchexecute_yqelme_response)
    out = {}
    if batch_text and "yQelMe" in batch_text:
        text = batch_text[4:].lstrip() if batch_text.startswith(")]}'") else batch_text
        if "\n" in text:
            parts = text.split("\n", 2)
            if len(parts) >= 3 and parts[1].isdigit():
                text = parts[2]
        norm = text.replace('\\"', '"')
        pat = re.compile(
            r'"https://photos\.fife\.usercontent\.google\.com/([^"]+)"\s*,\s*null\s*,\s*(\d{13})\s*,'
        )
        for m in pat.finditer(norm):
            path_part = m.group(1)
            ts_ms_str = m.group(2)
            try:
                ts_ms = int(ts_ms_str)
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                if 2000 <= dt.year <= 2030:
                    base_path = path_part.split("?")[0].strip()
                    if base_path:
                        out[base_path] = dt
            except (ValueError, OSError):
                pass

    print("Parsed dates:", len(out))
    if out:
        for i, (p, dt) in enumerate(list(out.items())[:5]):
            print(f"  {p[:50]}... -> {dt.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
