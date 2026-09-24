"""
Research-agent step 1b: retry pass.

For apps where the first crawl returned a JS-only shell (near-zero chars)
or an outright error, retry against a more specific, known docs URL
instead of the marketing homepage. Anything still failing after this is
recorded as a genuine crawler miss, not silently dropped.

Run:
    python scripts/fetch_retry.py
"""
import json
from pathlib import Path

from fetch_docs import fetch, clean_text, slugify, ROOT, RAW_DIR, LOG_FILE  # noqa

RETRY_URLS = {
    28: "https://developers.facebook.com/docs/whatsapp/cloud-api/overview",
    32: "https://developers.facebook.com/docs/marketing-api/overview",
    39: "https://developers.facebook.com/docs/threads/overview",
    34: "https://marketplace.gohighlevel.com/docs/",
    48: "https://help.gumroad.com/article/280-api-guide",
    52: "https://seranking.com/api.html",
    66: "https://neo4j.com/docs/http-api/current/",
    83: "https://binance-docs.github.io/apidocs/spot/en/",
    84: "https://www.paygent.co.jp/service/connect/",
    85: "https://ipayx.ai/docs/introduction",
    86: "https://developer.intuit.com/app/developer/qbo/docs/get-started",
    90: "https://pitchbook.com/data",
    94: "https://consensus.app/home/blog/",
    24: "https://open.larksuite.com/document/home/index",
}


def main():
    apps = {a["id"]: a for a in json.loads((ROOT / "data" / "apps.json").read_text(encoding="utf-8"))}
    log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    log_by_id = {e["id"]: e for e in log}

    for app_id, url in RETRY_URLS.items():
        app = apps[app_id]
        slug = slugify(app["name"])
        out_path = RAW_DIR / f"{app['id']:03d}_{slug}.txt"

        status, html, final_url, err = fetch(url)
        prev = log_by_id[app_id]
        print(f"[{app_id:>3}] {app['name']:<28} retry_url={url} status={status} err={err}")

        entry = {
            "id": app_id,
            "name": app["name"],
            "hint_url": app["hint_url"],
            "retry_url": url,
            "status": status,
            "final_url": final_url,
            "error": err,
            "saved_to": None,
            "chars_saved": 0,
        }

        if err or status is None or status >= 400:
            entry["ok"] = False
            entry["first_pass_chars"] = prev.get("chars_saved", 0)
        else:
            text = clean_text(html)
            if len(text) > prev.get("chars_saved", 0):
                out_path.write_text(text, encoding="utf-8")
                entry["ok"] = True
                entry["saved_to"] = str(out_path.relative_to(ROOT))
                entry["chars_saved"] = len(text)
            else:
                entry["ok"] = prev["ok"]
                entry["chars_saved"] = prev.get("chars_saved", 0)
                entry["saved_to"] = prev.get("saved_to")

        log_by_id[app_id] = entry

    new_log = list(log_by_id.values())
    new_log.sort(key=lambda e: e["id"])
    LOG_FILE.write_text(json.dumps(new_log, indent=2), encoding="utf-8")
    ok_count = sum(1 for e in new_log if e["ok"])
    print(f"\nDone. {ok_count}/{len(new_log)} have usable text after retry.")


if __name__ == "__main__":
    main()
