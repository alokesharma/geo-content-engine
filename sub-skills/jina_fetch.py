#!/usr/bin/env python3
"""Jina Reader batch fetcher for competitor pages (research sub-step 3, tier 2).

Fetches every URL through https://r.jina.ai/ in parallel and saves clean markdown.
Sits between WebFetch (tier 1) and Playwright (tier 3): Jina reads many pages that
403 / WAF-block a direct fetch, in 2-10s each, with no browser launch.

Usage:
    python3 sub-skills/jina_fetch.py --out runs/<run-id> <url1> <url2> ...

Writes  <out>/jina-<n>.md  for each successful read and prints one JSON summary:
    [{"n": 1, "url": ..., "ok": true,  "words": 1840, "file": "runs/.../jina-1.md", "title": ...},
     {"n": 2, "url": ..., "ok": false, "reason": "http 422"}]

A read is ok only if it is a real article: HTTP 200, >= MIN_WORDS words, the target
did not return an error status, and the page is not a bot wall / 404 page.
Each URL gets up to three tries: nav/footer stripped, then the raw page, then Jina's
headless-browser engine. "mode": "raw" means nav/footer text is still in the file, so
trim it before counting words for competitor-N-body.txt.
Exit code is always 0; the caller reads the JSON and sends failures to Playwright.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Optional. Jina Reader works without a key at a lower rate limit; a free key from
# https://jina.ai/api-dashboard raises it. Read from the environment, never hardcoded.
JINA_API_KEY = os.environ.get("JINA_API_KEY", "").strip()

MIN_WORDS = 500
TIMEOUT_S = 60
BOT_WALL = re.compile(
    r"just a moment|attention required|access denied|verify you are human|"
    r"are you a robot|captcha|request blocked|pardon our interruption|"
    r"enable javascript and cookies|couldn.t find that page|page not found|\b404\b",
    re.I,
)


def _call(url, strip_chrome=True, engine=None):
    headers = {
        "X-Return-Format": "markdown",
        "X-Retain-Images": "none",
        "X-Timeout": "45",
        "Accept": "text/plain",
    }
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"
    if strip_chrome:
        headers["X-Remove-Selector"] = "nav, header, footer, aside, form, .breadcrumb, .cookie"
    if engine:
        headers["X-Engine"] = engine
    req = urllib.request.Request("https://r.jina.ai/" + url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # timeout, DNS, reset
        return 0, f"{type(e).__name__}: {e}"


def _judge(status, text):
    """Return (ok, reason, title, body)."""
    if status != 200:
        return False, f"http {status}" if status else text[:120], "", ""
    title = ""
    m = re.search(r"(?m)^Title:\s*(.*)$", text)
    if m:
        title = m.group(1).strip()
    warn = re.search(r"(?m)^Warning:\s*(Target URL returned error.*)$", text)
    if warn:
        return False, warn.group(1).strip()[:120], title, ""
    body = text.split("Markdown Content:", 1)[-1].strip()
    words = len(body.split())
    if BOT_WALL.search(title) or (words < MIN_WORDS and BOT_WALL.search(body[:600])):
        return False, f"bot wall / error page (title: {title[:60]!r})", title, ""
    if words < MIN_WORDS:
        return False, f"thin: {words} words (< {MIN_WORDS})", title, ""
    return True, "", title, body


def fetch(n, url, out_dir):
    reason = ""
    # 1) chrome stripped  2) raw page (some sites, e.g. icicilombard.com, keep the article
    # inside <header>/<form>, so stripping empties it)  3) headless-browser engine
    for mode, strip_chrome, engine in (("stripped", True, None), ("raw", False, None),
                                       ("browser", False, "browser")):
        status, text = _call(url, strip_chrome, engine)
        ok, reason, title, body = _judge(status, text)
        if ok:
            path = os.path.join(out_dir, f"jina-{n}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\nSource: {url}\n\n{body}\n")
            return {"n": n, "url": url, "ok": True, "words": len(body.split()),
                    "h2": len(re.findall(r"(?m)^##\s", body)),
                    "mode": mode, "file": path, "title": title}
    return {"n": n, "url": url, "ok": False, "reason": reason}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="run directory to write jina-<n>.md into")
    ap.add_argument("urls", nargs="+")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda p: fetch(p[0], p[1], a.out), enumerate(a.urls, 1)))
    json.dump(res, sys.stdout, indent=1, ensure_ascii=False)
    print()
    good = sum(r["ok"] for r in res)
    print(f"jina: {good}/{len(res)} read", file=sys.stderr)


if __name__ == "__main__":
    main()
