"""
Builds the single self-contained report page (index.html at repo root) by
inlining data/apps.json, data/results.json and data/verification.json into
report/template.html. Re-run this after editing any data file.

Run:
    python scripts/build_report.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def inline(obj) -> str:
    return json.dumps(obj).replace("</", "<\\/")


def main():
    results = json.loads((ROOT / "data" / "results.json").read_text(encoding="utf-8"))
    verification = json.loads((ROOT / "data" / "verification.json").read_text(encoding="utf-8"))

    template = (ROOT / "report" / "template.html").read_text(encoding="utf-8")
    html = template.replace("__RESULTS_JSON__", inline(results))
    html = html.replace("__VERIFICATION_JSON__", inline(verification))

    out = ROOT / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html):,} chars)")


if __name__ == "__main__":
    main()
