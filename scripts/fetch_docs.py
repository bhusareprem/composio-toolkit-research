"""
Research-agent step 1: crawler.

Fetches the hint URL for every app in data/apps.json, strips boilerplate,
and saves cleaned text to data/raw/<id>_<slug>.txt for the extraction step
to read. Failures (blocked, JS-only, timeout, 404, etc.) are logged to
data/fetch_log.json instead of silently skipped -- a failed fetch is itself
a finding ("this app's docs actively resist automated research").

Run:
    python scripts/fetch_docs.py
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
APPS_FILE = ROOT / "data" / "apps.json"
RAW_DIR = ROOT / "data" / "raw"
LOG_FILE = ROOT / "data" / "fetch_log.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_CHARS = 8000


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "img"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)[:MAX_CHARS]


def fetch(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return resp.status_code, resp.text, resp.url, None
    except requests.exceptions.RequestException as exc:
        return None, None, None, str(exc)


def main():
    apps = json.loads(APPS_FILE.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log = []

    for app in apps:
        slug = slugify(app["name"])
        out_path = RAW_DIR / f"{app['id']:03d}_{slug}.txt"
        status, html, final_url, err = fetch(app["hint_url"])

        entry = {
            "id": app["id"],
            "name": app["name"],
            "hint_url": app["hint_url"],
            "status": status,
            "final_url": final_url,
            "error": err,
            "saved_to": None,
            "chars_saved": 0,
        }

        if err or status is None or status >= 400:
            entry["ok"] = False
        else:
            text = clean_text(html)
            out_path.write_text(text, encoding="utf-8")
            entry["ok"] = True
            entry["saved_to"] = str(out_path.relative_to(ROOT))
            entry["chars_saved"] = len(text)

        log.append(entry)
        print(f"[{app['id']:>3}] {app['name']:<28} status={status} ok={entry['ok']} chars={entry['chars_saved']}")
        time.sleep(0.3)  # be polite

    LOG_FILE.write_text(json.dumps(log, indent=2), encoding="utf-8")
    ok_count = sum(1 for e in log if e["ok"])
    print(f"\nDone. {ok_count}/{len(log)} fetched successfully. Log: {LOG_FILE}")


if __name__ == "__main__":
    main()
