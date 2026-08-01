---
name: internal-linking
description: Insert up to 3 internal links into a drafted article using the v21 3-slot structure (category pillar + category secondary + free topical) with DRAFT-FIRST anchoring — anchors are noun phrases already present in the prose, matched against the team-maintained link_map.json. Never force-inserts anchor text. Service-topic articles use service pages instead and skip the category pillar. Use after FAQ is added to the draft and before voice-pass. Triggers on "add internal links" or as part of content-gen-pipeline.
---

# internal-linking (v21 — draft-first, 3-slot)

Inserts internal links into the draft. Solves three failure modes from earlier pipeline versions: articles with zero internal links, hallucinated URLs that 404, and **irrelevant anchors** (the "add item" → `/adding-items-to-your-cart/` bug — a verb fragment carrying a link it doesn't describe).

**The core v21 principle: the draft decides the anchors, not the link list.** An anchor is always a noun phrase that already exists in the prose. If no natural phrase exists for a slot, that slot ships empty. Nothing is ever inserted, reworded, or forced to carry a link — with one narrow exception for the pillar (Step 1).

**v22.6 perf — URL verification budget (this phase used to cost ~6 min for 3 links; target ≤2 min):**
- **URLs from `link_map.json` (pillar + secondary pools + service pools) are PRE-VERIFIED by the team. Use them as-is — ZERO live checks.** No WebSearch, no WebFetch, no status probe on a map URL. The map is the trust boundary; if a map URL ever 404s in review, the team fixes the map (one line), not the pipeline.
- **URLs already captured in `research-brief.md` §6 were verified during research. Do not re-verify them here.**
- **Only a NOVEL slot-3 topical URL** (found fresh via `WebSearch site:example.com` in this phase) needs that one WebSearch as its verification — the search result IS the existence proof. One search, not a search-then-fetch chain.
- Net: a normal run performs at most ONE live lookup in this whole phase (the fresh slot-3 search), and zero when slot 3 comes from the brief or ships empty.

---

## When to use

After `draft.md` and `faq-builder.md` have run; the draft must include the body and the FAQ. Before `voice-pass.md` so any anchor-text issues get caught by the voice pass.

---

## Inputs

- `draft.md` (with FAQ already appended)
- `sub-skills/link_map.json` — the team-maintained pillar map, per-category secondary pools, and service pools (source: the team's "Link Logic" sheet)
- `research-brief.md` §6 (brand context — pre-discovered your-site URLs, used only for Slot 3 candidates)
- `content_rules.md` §4 (anchor text rules)

---

## Step 0 — Classify the article: category or service

Check the topic against `config.service_topic_keywords` in `style.json` (account setup, login help, order status, returns, shipping tracking, warranty registration…).

- **Category article** → follow the 3-slot structure below.
- **Service article** → links come from `link_map.json` → `service_pools` (plus genuinely topical pages). Do NOT force a category pillar or category secondary links into a service article — an order-tracking how-to does not need a product-category plug. `validate.py` skips the `pillar_link` check automatically when the topic matches a service keyword. Max 3 links and all anchor rules still apply.

## The 3-slot structure (category articles) — max 3 links total

| Slot | What | Source | Mandatory? |
|---|---|---|---|
| 1 | Category pillar | `link_map.json` → `pillar_map` | YES |
| 2 | Category secondary | `link_map.json` → `secondary_pools[<category>]` | No — only if a natural anchor exists |
| 3 | Free topical page | any relevant page on your site (research-brief §6 or WebSearch `site:example.com`) | No — only if a natural anchor exists |

Pillar map (one per category). A pillar page is your main category/hub page — the top-level landing page for a vertical. The configured verticals below are illustrative; swap for your own hubs:

| Category | Pillar URL |
|---|---|
| Guides | `https://example.com/guides/` |
| Products | `https://example.com/products/` |
| Pricing | `https://example.com/pricing/` |

### Step 1 — Slot 1: the pillar link (mandatory)

- Find the first natural occurrence of the bare vertical name in the body ("guides", "products", "pricing", or your configured vertical name) **from the 3rd substantive paragraph onward** and link it to the pillar URL.
- **Narrow exception to draft-first:** if the bare vertical name genuinely does not appear in the body, add it naturally to one early sentence, then link it. Never force awkward phrasing. (This is the only place text may be touched for a link — the pillar is the one mandatory link, and the vertical name fits naturally in any article about that vertical.)
- Exactly one pillar link per article. Missing pillar = `validate.py` `pillar_link` FAIL → no delivery.

### Step 2 — Slot 2: the category secondary (draft-first)

1. Load the article's category pool from `link_map.json` → `secondary_pools`.
2. **Scan the draft for natural noun phrases (2–6 words)** that name one of the pool's pages — e.g. prose that says "a height-adjustable standing desk guide" matches the "Standing Desk Guide" pool entry; "picking an annual pricing plan" matches "Annual Pricing Plan".
3. Match = the phrase shares ≥2 meaningful nouns with the pool entry's URL slug (this is exactly what `validate.py`'s `anchor_quality` check enforces).
4. Pick the single best match (most specific phrase, most relevant page). Link that existing phrase — change zero words.
5. **No natural match in the whole pool → Slot 2 ships empty.** Do not insert a sentence to create one.

### Step 3 — Slot 3: the free topical link (draft-first)

1. Candidates: your-site URLs from `research-brief.md` §6, or a fresh `WebSearch site:example.com <phrase>` for promising noun phrases in the draft. Any page on your site is eligible if genuinely topical (including service pages where the topic touches them).
2. Same draft-first rule: only link a noun phrase already in the prose, ≥2 noun overlap with the target slug.
3. No natural match → Slot 3 ships empty.

### Anchor rules (all slots — enforced by `validate.py` `anchor_quality` + `anchor_self_scoping`, publish-blocking)

- Anchor is a **noun phrase already in the prose** — never a verb fragment ("add item" ✗), never inserted text
- 2–6 words
- **Take the LONGEST natural noun phrase at that spot (v22.5).** If the prose says "a standing desk guide is the closer fit", the anchor is "standing desk guide", NOT "standing desk" — never trim a scoping word off the end of the phrase you're linking.
- **The anchor must self-scope (v22.5, the "generic term" fix).** Read the anchor ALONE, outside its sentence: it must still read as an on-topic phrase. A bare generic term ("damage" — a generic word standalone) fails; it needs a scoping word inside the anchor (guide / plan / product / review / pricing / setup…) or must itself be a self-scoping proper term (a brand or product name). Both lists live in `style.json` (`anchor_scoping_tokens`, `anchor_proper_terms`) — team-editable. Enforced by `validate.py` `anchor_self_scoping` (FAIL). If no scoping word exists in the prose phrase, the slot ships empty — do not insert one.
- Shares ≥2 meaningful nouns with the target URL's slug (pillar links exempt — their anchor is the bare vertical name)
- Reads naturally in its sentence; IS the subject of the linked page
- No "click here", "learn more", "this article", "read more"
- No link in the lede or first 2 paragraphs; any two links ≥1 paragraph apart (`link_para_spacing`)
- Every URL on example.com; no duplicate URLs; never a naked URL

### Optional GSC anchor refinement (v22.5 — runs only when the GSC MCP is connected)

After picking each contextual anchor (Slots 2–3), if the GSC MCP tools are available (`mcp__gsc__*`), refine the anchor SPAN — never the target:

1. Query GSC for the target URL's top search queries (e.g. `advanced_search_analytics` filtered by page = the target URL, last 90 days, top 10 by impressions).
2. Compare the candidate anchor against those queries. If a **longer prose phrase at the same spot** matches the page's real queries better (e.g. the page ranks for "best standing desk for small spaces" and the prose offers "standing desk guide"), extend the anchor to that phrase.
3. Record `gsc_queries_checked: true` and the top query in the audit entry. If GSC is not connected, record `gsc_queries_checked: false` and move on — this step never blocks and never changes which page is linked, only how much of the existing prose phrase the anchor covers.

---

## Output

`draft-linked.md` — the draft with up to 3 internal links inserted inline.

Also `internal-linking-audit.json` (consumed by `validate.py`'s interlink-audit check):

```json
{
  "skill": "internal-linking",
  "status": "PASS" | "PARTIAL" | "FAIL",
  "article_class": "category" | "service",
  "links": [
    {"slot": "pillar", "anchor": "guides", "url": "https://example.com/guides/", "anchor_source": "draft"},
    {"slot": "secondary", "anchor": "standing desk setup guide", "url": "https://example.com/guides/standing-desk-setup/", "anchor_source": "draft", "slug_noun_overlap": ["standing", "desk", "setup", "guide"]},
    {"slot": "topical", "anchor": "...", "url": "...", "anchor_source": "draft"}
  ],
  "slots_empty": [
    {"slot": "topical", "reason": "no natural noun phrase in draft matched any candidate page"}
  ]
}
```

`anchor_source` is always `"draft"` — it asserts the anchor phrase pre-existed in the prose (pillar's narrow exception still records `"draft"` after the vertical name is woven in). A missing/invalid audit file or a link without a valid slot = FAIL.

---

## Hard checks

- **Pillar link present for category articles: exactly one bare-vertical-name anchor → pillar URL. Missing = FAIL.** (Skipped for service articles.)
- **Max 3 links total** (`link_count_max`, config `max_links_total: 3`)
- **Every anchor passes `anchor_quality`**: 2–6 word noun phrase, ≥2 noun overlap with target slug
- Slot 2 URL comes from the article's category pool in `link_map.json`
- Every URL is on example.com and traces to `link_map.json`, `research-brief.md` §6, or a WebSearch result from this run (no hallucinated paths)
- No forum/social links (`no_forum_links`); links ≥1 paragraph apart (`link_para_spacing`); no link in paragraphs 1–2
- Empty slots are recorded with a reason in the audit — fewer links is always acceptable; a forced anchor never is

---

## What it prevents

- Irrelevant/verb-fragment anchors carrying links they don't describe (the "add parent" bug)
- Force-inserted anchor text that breaks the prose register
- Articles published with zero internal links, or hallucinated URLs that 404
- Category links shoehorned into service articles (order-tracking/returns/warranty readers aren't in a shopping moment)
- Link clustering and generic anchor text

---

## Notes for the builder

- `link_map.json` is team-owned, like `style.json`. When marketing adds a landing page, add one line to the right pool — no prose edits needed.
- If a source-sheet row points its hyperlink at the wrong URL (a copy-paste error), exclude that row and re-add it once the sheet is fixed.
- GSC is no longer used for anchor SELECTION (the v20.x GSC procedure picked keyword-first anchors, which caused the irrelevant-anchor bug). v22.5 reintroduces GSC only as optional anchor-span REFINEMENT: the draft still decides the anchor phrase; GSC data may only extend that phrase to match what the target page actually ranks for. GSC remains optional research input in Phase 1.

