---
name: research-flow
description: Bundled research skill (v20.5 PRODUCTION). Calls SerpAPI (India geo) for SERP num=20, AI Mode, Forums, News, Videos; Ahrefs (limit=10) for related terms + question terms; WebFetch+Playwright for competitor depth; Reddit JSON for community signal; GSC MCP for Acme URL graph. AI Overview retired (v12 #76 -- AI Mode is the BLUF signal). Outputs research-brief.md.
---

# research-flow

Replaces hallucinated SEO research with real, current, external data. Runs five sub-steps and bundles them into one handoff file that every downstream Generate skill reads.

This is the single most important skill in the pipeline. If research-flow produces a thin brief, every downstream skill produces thin output.

---

## When to use

First stage of any pipeline run, before any Generate skill. Also usable standalone when the team needs research on a topic without writing an article.

---

## Inputs

- `topic` (required) — the keyword or topic phrase
- `vertical` (optional) — health, car, bike, gmc, travel, life

---

## Credentials (from environment variables)

> Keys are read from the environment, never hardcoded. Copy `.env.example` to `.env` and add your own keys. Load them into the shell before a run (for example `set -a; source .env; set +a`), or export them directly.

```
SERPAPI_KEY        = os.environ["SERPAPI_KEY"]         # serpapi.com dashboard
AHREFS_API_TOKEN   = os.environ["AHREFS_API_TOKEN"]    # Ahrefs dashboard -> API (only if you call the REST API directly)
```

Ahrefs can also run via the connected Ahrefs MCP tools (`keywords-explorer-matching-terms` etc.), in which case no token is needed in the shell. If you call the Ahrefs REST API directly, read the token from `AHREFS_API_TOKEN`.

The optional Google Docs delivery uses OAuth `credentials.json` — see `optional/google-docs-delivery/`. It is not part of the default (local Markdown) path.

---

## Process

Each sub-step writes its raw output (JSON) to the session folder. The final sub-step bundles into a markdown brief.

### Sub-step 1 — Keyword + SERP intelligence (v20.5 PRODUCTION — Ahrefs RESTORED with limit=10)

**v20.5 change.** Ahrefs is back, but locked at `limit=10` on both calls — drops cost ~90% vs the v20.1 default that burned through quota.

**Two Ahrefs calls only** (same endpoint, different filter):

1. **Related-term pool — `keywords-explorer-matching-terms`** with `country=in`, `keywords=<topic>`, `limit=10`. Top 10 related terms by volume. Feeds SEO meta + body keyword variants.
2. **Question pool — `keywords-explorer-matching-terms`** with `country=in`, `keywords=<topic>`, `limit=10`, `terms=questions` (native Ahrefs filter for question-shaped keywords). Top 10 question-form variants. Feeds FAQ source pool.

Do NOT call `keywords-explorer-related-terms` (replaced by the two filtered matching-terms calls above) or `keywords-explorer-overview` (head-term bias caused v20.1's irrelevant anchors).

Every keyword that appears in the article must trace verbatim to one of: (a) the 10 related terms above, (b) the 10 question terms above, (c) SerpAPI `related_questions` (PAA), (d) SerpAPI `related_searches`, (e) Google autocomplete, (f) competitor H1/H2/H3 strings, or (g) the topic phrase itself. The validator FAILs a made-up keyword (#62).

Save Ahrefs results to `ahrefs-keywords.json` (related terms) and `ahrefs-questions.json` (question terms).


### Sub-step 2 — PAA + zero-volume fallback

Call SerpAPI with the key from the environment:
`https://serpapi.com/search.json?engine=google&q=<topic>&gl=in&hl=en&num=10&api_key={SERPAPI_KEY}`

- Capture `related_questions` (PAA box)
- Capture `related_searches`
- If sub-step 1's keyword overview returned empty for all variants, treat SerpAPI's `organic_results` as the primary SERP source

**Keyword pool (#62 — zero made-up keywords).** The keyword pool is drawn ONLY from real captured sources: the Ahrefs related + question terms (sub-step 1), SerpAPI `related_questions` (PAA), `related_searches`, Google autocomplete, the H1/H2/H3 headings scraped from competitors (sub-step 3), and the exact topic phrase. NEVER synthesize or stitch a keyword variant. Every keyword that appears in the SEO audit must trace verbatim to one of these captured lists.

Save to `paa.json`, `serpapi.json`, .

### Sub-step 2b — AI Mode (primary AI-answer signal for the BLUF) — v12

AI Overview is volatile and often returns no fetchable token (the v9/v11 failure). **Google AI Mode is the reliable substitute** — query it directly, no `page_token` expiry:
`https://serpapi.com/search?engine=google_ai_mode&q=<topic>&gl=in&hl=en&location=India&api_key={SERPAPI_KEY}`

> **v20.3 — India geo is MANDATORY on every SerpAPI call.** Without `gl=in&hl=en&location=India`, SerpAPI returns US-leaning answers (ACA / federal / Grandfathered / HIPAA — exactly what v20.2's AI Mode capture pulled). Apply the same trio of params to: `engine=google` (main SERP, line above), `engine=google_ai_mode`,  page-token call, `engine=google_forums`, `engine=google_news`, `engine=google_videos`. validate.py FAILs the run if `ai-mode.json` text_blocks contain US-context markers and the article is India-targeted (default).
Save the generated answer + its cited sources to `ai-mode.json` (brief §2b). The draft uses this to model what the BLUF/opening must cover (the question framing + sub-points Google's AI rewards). **Signal, not source text: paraphrase only, no verbatim span over ~8 words may match the AI Mode text** (anti-copy gate; canon G3). Keep AIO as a bonus if a token does appear.

### Sub-step 2c — Forums, News, Videos (v12)

- **Google Forums** (`engine=google_forums&q=<topic>&gl=in&hl=en&location=India`): widen community signal beyond Reddit+Quora. Pull thread titles, questions, and pain points. Save to `forums.json` (brief §4.5). Feeds FAQ sourcing and real-user body angles. India geo is mandatory (v20.3).
- **Google News** (`engine=google_news&q=<topic>&gl=in&hl=en&location=India`): **only when the topic is time-sensitive** (a recent rule change, event, fresh circular). Use it as a TIP-OFF to locate the PRIMARY gov/IRDAI source — NEVER cite a news outlet in the body (gov-only rule, canon C4). For evergreen topics, skip. Save to `news.json` if used.
- **Google Videos** (`engine=google_videos&q=<topic>&gl=in&hl=en&location=India`): store the top ranking videos. Where a transcript is available, extract genuine non-commodity insights and FAQ candidates — paraphrase only, never lift, and a video is not a citable authority (structural/FAQ signal only). Save to `videos.json` (brief §4.6).

### Sub-step 3 — Competitor depth (target: 5 successful deep reads — "5 means 5")

Goal: **5 fully-read competitor articles.** Not 5 attempts — 5 successes. Work down the SERP list (top 5, then 6, 7, 8…) until 5 reads succeed.

**v22.6 perf — fetch in BATCHES, never one at a time (this sub-step used to cost ~3 min; batching cuts it to under 1):**
1. **Batch 1 — parallel WebFetch.** Take the top 7 SERP candidates (over-fetch 2 to absorb failures) and issue ALL 7 `WebFetch` calls in a SINGLE message so they run in parallel. Accept every result with ≥500 words of body text.
2. **Batch 2 — ONE Playwright launch for all failures.** Collect the URLs that returned <500 words, errored, 403'd, or timed out, and run the batch helper below on all of them in one go. Do NOT launch a browser per URL, and do NOT skip to "Playwright unavailable" — actually execute this code. Playwright is installed and verified.
3. **Still short of 5?** (hard anti-bot like a Cloudflare challenge on some URLs) — mark those `blocked`, take the next 2-3 SERP results (#8, #9…) as another parallel batch, and repeat until 5 URLs are successfully read.

**Playwright batch helper — run this exact code (do not improvise):**
```python
from playwright.sync_api import sync_playwright

def fetch_rendered_batch(urls, timeout_ms=60000):
    """v22.6: ONE chromium launch for the whole batch (was one launch per URL).
    domcontentloaded + 2s settle instead of networkidle: ad-heavy news sites never
    reach networkidle and used to burn the full 90s timeout."""
    out = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in urls:
            ctx = browser.new_context(
                user_agent=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"),
                viewport={"width": 1366, "height": 900},
                locale="en-IN",
            )
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(2000)  # let late JS settle
                out[url] = page.inner_text("body")
            except Exception:
                out[url] = ""       # caller treats "" as a failed read
            finally:
                ctx.close()
        browser.close()
    return out
```
Run it via the same `python3` confirmed to have Playwright (`python3 -c "import playwright"` returns OK on this machine).

**For each successful read, extract:** H1, all H2s, all H3s, FAQ section if present, named numeric claims, IRDAI citations. Save as `competitor-1.md` through `competitor-5.md`.

**Comparison topics (v22):** if the topic is a comparison (`vs` / `versus` / `difference between` / `X or Y`), also capture the factor-by-factor contrast facts (weight, cost, coverage, eligibility, etc.) — note them as plain facts, and if a competitor page has a comparison table, record the *facts* it conveys, NOT its wording. Save to `comparison-facts.md`. The draft paraphrases these into Acme's own comparison table (never copy a competitor table verbatim — that is plagiarism). Corroborate each fact across ≥2 sources where possible.

**Also save the CLEAN body text (v21 — for the length target).** For each successful read, save the article's main body (boilerplate removed) to `competitor-N-body.txt`. Use `trafilatura` if available (`python3 -c "import trafilatura; print(trafilatura.extract(html))"`) — it strips nav/header/footer/sidebar and returns just the article. If trafilatura isn't installed, use the WebFetch markdown (already largely de-chromed) and count that; do NOT use raw Playwright `inner_text("body")` for the count (it includes the whole nav/footer and inflates word counts). This file is what makes the competitor word count honest.

### Sub-step 3c — Compute the length + coverage target (v21)

After the competitor reads, run the deterministic helper:
```bash
python3 sub-skills/length_target.py runs/<run-id>
```
It reads `competitor-N.md` (H2 counts) + `competitor-N-body.txt` (clean body words), takes the **median** of each (median, not mean — one long outlier shouldn't skew the target), and writes `length-target.json` with: the word-count band (median ×0.85–1.25, clamped to floor 800 / ceiling 2800), the **section_target** (median competitor H2 count), and a per-section word cap. The draft and validator both read this file. If no competitor body was captured it writes a safe default band and says so. **Length is a byproduct of coverage — the article hits the section_target with real, grounded sections; it is never padded to a word number.**

**Hard rule:** if after exhausting the top ~10 SERP results fewer than 5 reads succeed, record the count and the per-URL failure reason in the status — but the strong default is 5 successful reads. Backfilling to lower-ranked results is expected and correct; the top 5 are preferred but not mandatory if a specific site hard-blocks even Playwright.

### Sub-step 4 — Community signal

For Reddit — v22: use the **Arctic Shift** public archive API (https://github.com/ArthurHeitmann/arctic_shift), NOT reddit.com and NOT SerpAPI snippets. Arctic Shift mirrors Reddit posts+comments, needs no auth, is not IP-blocked, and returns FULL body text (real thread depth, not a search snippet). This replaces the old SerpAPI `site:reddit.com` snippet method (titles-only) and the dead direct-`reddit.com/*.json` method (403 from datacenter IPs). Do NOT call reddit.com.
- **Posts:** `GET https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=<sub>&query=<terms>&limit=10&sort=desc`. **The API rejects a bare `query` with HTTP 400 — a `subreddit` (or `author`) param is REQUIRED alongside `query`.** For insurance topics good subs are `personalfinanceindia`, `IndiaInvestments`, `insurance`, `HealthInsurance`, `india`. Keep query terms short (1-2 key nouns); over-long queries return 422; a 429 means back off ~2s and retry once.
- **v22.6 call budget: 2 subs × 2 queries = max 4 calls up front.** Pick the 2 subs most relevant to the topic (not a fixed pair — a car topic wants `CarsIndia`/`india`, a health topic `personalfinanceindia`/`HealthInsurance`). The 2026-07-14 run made 8 calls across 4 subs, pulled 16 threads, and the article used ONE — the marginal subs add latency, not signal. **Expand to more subs ONLY if the first 4 calls yield fewer than 3 usable threads** (on-topic, non-removed, with real bodies).
- **Comments (this is the fix — real user insight lives here):** for the top posts, `GET https://arctic-shift.photon-reddit.com/api/comments/search?link_id=<post_id>&limit=50&sort=desc`. Capture `body` + `score`; keep the highest-scored, non-removed comments as the community insight. Paraphrase only — never lift a verbatim span (canon G3 anti-copy still applies).
- Capture per post: `id`, `title`, `selftext`, `permalink`, `score`, `subreddit`, `num_comments`.
- Save as `reddit-serp.json` in this exact shape so `lineage_check.py` can fingerprint it unchanged: `{"threads": [{"title": "...", "insight": "<top comment or selftext, paraphrased>", "url": "..."}]}`. Record the sub-step PASS with `method: arctic-shift`.
- Only if Arctic Shift is unreachable (5xx) or returns zero results for both queries: fall back to SerpAPI `site:reddit.com` snippets (`engine=google&q=site:reddit.com <topic>`) and record `method: serpapi-fallback` with the reason; if that is also empty, record SKIPPED (Quora + PAA + Forums carry community signal).

For Quora:
- WebSearch `site:quora.com <topic>` (Quora has no open search JSON; WebSearch titles are the reliable signal)
- Capture question titles only (Quora blocks full-thread scraping)
- Save to `quora-titles.json`

### Sub-step 5 — Acme context + URL graph

For Acme format reference (GSC is optional — skip if not connected):
- If a GSC connection is available, call `quick_wins` filtered to position 4-15 for queries related to the topic. This surfaces Acme pages already ranking well on adjacent terms — useful as format reference.
- GSC here is INPUT data (Search Console performance), not document output. It is optional; if unavailable, proceed using WebSearch site:acme.com alone for the URL graph.

For internal-link URL graph:
- WebSearch `site:acme.com <topic-phrase-variants>`
- Capture the real URLs Acme already has on related topics
- Save to `acme-gsc.json` and `acme-urls.json`

### Sub-step 5b — Acme KB (car vertical ONLY, factual extraction)

If and only if `vertical == car`, read the Acme knowledge base at `canon/acme-kb-car.txt`. It is a set of Acme sales-call scripts, so treat it as a FACTUAL source only: extract coverage facts, base-policy inclusions, and add-on definitions (e.g. "Engine Protect covers water ingress", "rat-bite cover is in the base own-damage policy"). **Strip every pitch, plan-sell, IDV pitch, and objection-handling line — never mirror its salesy register** (canon E2). Save the extracted facts to `acme-kb-facts.json` for the draft to use as bullets/chunks. For non-car verticals, skip this entirely.

### Sub-step 6 — Data enrichment (the differentiator)

Hunt for citable, relevant data that makes the article non-commodity (canon Rules #28, #29, #32). This is the single highest-value research step for GEO.

- WebSearch for relevant statistics, studies, surveys, and regulatory reports on the topic. Good sources: IRDAI annual reports + circulars, GI Council, credible industry surveys, dated news data.
- For each data point found, capture a tuple: `{stat, exact_metric_name, value, publisher, exact_source_url, date}`.
  - **`exact_metric_name` is mandatory and is the source's own wording** (e.g. "incurred claims ratio", not a paraphrase). This is the input to the draft's metric-label fidelity (canon Rule #49). Never relabel a metric. If a value looks impossible for a common label (a ratio >100% is NOT a "claim settlement ratio"), record the source's literal label and a `label_warning: true` flag.
  - **`date` captures the data vintage** (e.g. "FY24", "March 2024") so the draft can state currency explicitly (canon Rule #48).
- Only keep stats genuinely relevant to the topic. Discard tangential numbers.
- **Source quality: primary over aggregator (v8, #64, canon Rule #55).** Prefer the primary/authoritative publisher (IRDAI, GI Council, official filings). If you find the figure only in a third-party aggregator's *summary* (e.g. "Algates Insurance summary of IRDAI Annual Report"), locate and cite the primary IRDAI source it summarizes; if the primary can't be found, flag the stat rather than cite the aggregator recap. Never record an insurance aggregator/competitor as the publisher of a regulator figure.
- **Cap the must-include set at the 2 strongest external statistics (canon Rule #43).** Rank by: (a) does it change the reader's decision, (b) authority of publisher, (c) recency. Keep the top 2 as `must-include`; everything else is `nice-to-have` and the draft will NOT use it as a cited stat. IRDAI regulatory clause/rule citations do NOT count against this cap — they are the legal backbone, not statistics.
- **One publisher per stat. Never merge two sources into one citation** (canon Rule #44). If two sources report the same figure, keep the more authoritative one only.
- Surface where Acme's own internal data WOULD strengthen the article (especially the one mandatory expert verdict, canon Rule #41), and flag it `[Acme internal data needed — team to supply]`. **This flag belongs in a "Team to supply" appendix the draft keeps OUT of body prose (canon Rule #47).** Never invent Acme figures.
- Save to `data-enrichment.json`.

Note: every stat that survives into the draft must carry a single-publisher `[Source: Publisher]` link per canon Rules #34 and #44. This sub-step supplies the source URLs and exact metric names that make that possible.

### Sub-step 7 — Bundle

Compile all sub-outputs into one Markdown `research-brief.md` with explicit numbered sections:
- §1 Keyword intelligence (with table)
- §2 Live SERP top 10
- §3 Competitor depth (one sub-section per competitor)
- §2b AI Mode answer (BLUF modeling, paraphrase only)
- §4 Question pool — §4.1 PAA (SerpAPI related_questions), §4.2 Reddit, §4.3 Quora, §4.4 related_searches, §4.5 Forums (Google Forums), §4.6 Videos (Google Videos transcripts/insights); plus §2c News (only if time-sensitive, tip-off only).
- §5 Information gain (gaps the competitors leave open)
- §6 Acme context
- §7 **Data enrichment** — the ≤2 must-include stats (each with exact metric name + value + single publisher + source URL + date vintage) and nice-to-have stats; plus a separate "Team to supply" sub-list holding every `[Acme internal data needed]` flag (these never enter body prose)
- §8 Targeting parameters (locked for Generate Flow) — including the length + coverage target from `length-target.json` (word band, section_target, per-section cap)

Also write `research-execution.json` with the status of each sub-step (PASS / FAIL / PARTIAL / SKIPPED, with reason).

---

## Output

- `research-brief.md` — the single handoff file
- All intermediate JSON files retained in session folder
- `research-execution.json` for the data-lineage-auditor to consume

---

## Hard checks

- Sub-step 1 OR sub-step 2 must return SERP top 10. If both fail, halt with "no SERP data" error.
- Sub-step 3 must successfully read at least one competitor. If all three fail, halt with "no competitor depth" error.
- Sub-step 5 must return at least 5 Acme URLs. If fewer than 5, log warning but proceed.
- Every sub-step writes a status entry to `research-execution.json`.

---

## What it prevents

- Hallucinated SEO data (the v1 failure where ChatGPT made up volume and SERP)
- Silent zero-volume failures (SerpAPI fallback wired in)
- Missing community signal (a real v1/v2 failure)
- Hallucinated internal URLs (only real WebSearch-verified URLs proceed)

---

## Notes for the builder

- Sub-steps 1, 2, 3, 4, 5 can run in parallel after sub-step 1 surfaces the SERP URLs needed by sub-step 3.
- Reddit `.json` trick works without auth on public threads. Reddit may rate-limit at scale; consider caching responses.
- Quora aggressively blocks scraping. Titles via WebSearch is the reliable signal; do not try to scrape thread bodies.
- Keep this skill bundled. Splitting the 5 sub-steps into 5 skills adds maintenance overhead with no operational benefit.


## v20.6.4 RUNTIME OPTS (target: 1-1.5hr -> 30-45min total)

### R5 -- Skip Playwright on known-block domains

DO NOT attempt Playwright fallback on policybazaar.com or bankbazaar.com. They consistently 403 / hit WAF. Record `SKIPPED -- WAF blocked (known)` without retry. Saves 60-120s per URL.

### R1 + R2 + R7 -- Parallelize INDEPENDENT tool calls

When multiple tool calls in the same phase have NO output dependency between them, issue them as concurrent tool blocks in ONE message:

**Phase 1 SerpAPI batch (saves 30-60s):**
- engine=google (SERP), engine=google_ai_mode, engine=google_forums, engine=google_videos
- All 4 in ONE assistant turn with parallel tool calls.

**Phase 2 competitor scrapes (saves 60-90s):**
- All 5-6 publisher URLs to WebFetch in ONE message as parallel tool calls.
- Any Playwright fallbacks batched in the NEXT message (also parallel).

**Phase 5 (GSC) + Phase 7 (SEO meta) + Phase 8 (lineage) (saves 30-60s):**
- These have no input dependency on each other after draft is final. Run in parallel batches.

**Discipline:** if you find yourself making 5 tool calls in 5 separate messages, you are doing it wrong. Batch independent calls.

