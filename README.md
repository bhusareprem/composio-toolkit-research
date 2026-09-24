# Composio Toolkit Research — AI Product Ops Intern take-home

**Live case study:** see the deployed link in the submission / repo description.
**This repo:** the research agent, the raw data, and the page it produces.

## What this is

Composio turns apps into agent-callable tools. Before building a toolkit for an app, someone
has to research it: auth model, self-serve vs. gated access, API surface, and whether it's
buildable today. This repo does that for 100 apps, with an agent doing most of the legwork
instead of a human filling in a spreadsheet by hand — see the case study for the patterns,
the honest misses, and the verification loop that caught them.

## Repo layout

```
data/
  apps.json          the 100 apps + category + hint URL, as given in the brief
  fetch_log.json      per-app crawl status (success/failure, chars fetched) from both crawl passes
  raw/                 cleaned text scraped from each app's docs (crawler output)
  results.json         the 100 structured findings: auth, access, API surface, buildability, evidence
  verification.json    the 10-app manual verification sample: hits, misses, corrections, accuracy
scripts/
  fetch_docs.py         stage 1: crawls all 100 hint URLs, saves cleaned text + a fetch log
  fetch_retry.py         stage 2: retries the ~9 apps that failed or came back as an empty JS shell
  build_report.py        inlines results.json + verification.json into report/template.html -> index.html
report/
  template.html          the page template (placeholders get replaced by build_report.py)
index.html                the built, single-file, self-contained case study (generated — don't hand-edit)
```

## How the research agent actually worked

1. **Crawl** (`python scripts/fetch_docs.py`) — plain HTTP requests + BeautifulSoup against all
   100 hint URLs. No JS rendering, no auth. Logs status codes and saves cleaned text. Got usable
   text for 91/100 on the first pass.
2. **Retry** (`python scripts/fetch_retry.py`) — for the 9 that failed (blocked, 404, or an
   empty JS-only shell), retries against a more specific known-docs URL instead of the marketing
   homepage. Got to 94/100.
3. **Extraction** — the remaining thin/ambiguous cases (and everything needing a real verdict on
   auth model + self-serve-vs-gated) were resolved by an LLM (Claude, via Claude Code, in the
   session that produced this repo) reading the crawled text plus targeted web searches for ~20
   apps where the crawl alone wasn't enough (niche fintechs, brand-new AI-native tools, anything
   behind Meta's bot-blocking). This step is **not** a fully unattended script in this repo,
   because doing it unattended requires an LLM API key this environment didn't have, and
   Composio's own toolkit catalog would have been the fastest cross-check but requires creating
   an account — which wasn't done on the user's behalf. See "Running it yourself" below for how
   to wire in a real key and make this step unattended.
4. **Verification** — 10 of the 100 apps were sampled and checked by hand in a real browser
   against their actual docs pages. Two real misses were found and corrected directly in
   `results.json` (Gumroad's API was wrongly downgraded because the crawl hit a dead help-center
   link; iPayX was wrongly written off as unverifiable when it's actually a real, unusually
   agent-forward product). Full detail in `data/verification.json` and the case study's
   Verification section.

## Running it yourself

```bash
pip install requests beautifulsoup4

# Stage 1: crawl all 100 apps
python scripts/fetch_docs.py

# Stage 2: retry the ones that failed or came back empty
python scripts/fetch_retry.py

# Rebuild the report from the current data files
python scripts/build_report.py
# -> writes index.html at the repo root; open it directly or serve it:
python -m http.server 8080
```

To make stage 3 (structured extraction) unattended instead of LLM-in-the-loop, wire a
Gemini or Anthropic API key into a new `scripts/extract.py` that reads `data/raw/*.txt` and
`data/fetch_log.json`, and asks the model to emit the same schema as `data/results.json`
(see `data/apps.json` for the 6 fields the brief asks for, plus `mcp` and `confidence` which
this repo added). That script isn't included because this environment had no spare key to
build and test it against — see the case study's Honesty section for why that's disclosed
rather than faked.

## Data schema (`data/results.json`)

Each of the 100 entries has:

| field | meaning |
|---|---|
| `category`, `one_liner` | as given in the brief |
| `auth` | array of auth methods (OAuth2, API key, Basic, custom scheme, etc.) |
| `access` | `self-serve-free` / `self-serve-trial` / `self-serve-paid` / `self-serve-reviewed` (self-serve signup, but an approval gate blocks production) / `customer-gated` (must already be a paying customer of the product itself) / `partner-gated` / `contact-sales` / `unverified` |
| `access_note` | one or two sentences of evidence for the access verdict |
| `api_surface` | REST/GraphQL/proprietary, and roughly how broad |
| `mcp` | whether an official/community/claimed MCP server exists |
| `buildability` | `yes` / `yes-with-limits` / `no` |
| `blocker` | the specific thing in the way, if any |
| `evidence` | the docs URL(s) behind the verdict |
| `confidence` | `high` / `medium` / `low` — how sure the agent was before verification |
| `verification_note` / `crawler_note` | present only on the ~15 rows touched by the manual verification pass or where the crawler hit something notable (e.g. Meta's 400s) |

## Notes on honesty

Two apps in the list — **Paygent Connect** and **iPayX** — have no independently verifiable
public API documentation, even after crawling, searching, and manually browsing. Per the
brief's own rule, that's reported as the finding, not hidden. Full detail in the case study's
Honesty section and in `data/results.json` entries 84 and 85.
