---
name: seo-meta-builder
description: Generate SEO meta title (50-60 chars), meta description (145-160 chars), and slug for a blog article. Audit primary keyword placement across title, meta, slug, H1, first 100 words, and at least one H2. Trace each Ahrefs cluster keyword to where it appears in the article body. Reads structure_rules.md for title and meta description rules. Use after voice-pass and before data-lineage-auditor. Triggers on "build SEO meta" or as part of content-gen-pipeline.
---

# seo-meta-builder

Builds the on-page SEO metadata that gates whether the article ranks. Title, description, slug. Plus an audit table proving the primary keyword and cluster keywords landed in the right places.

---

## When to use

After `voice-pass.md` has cleaned the draft. Before `data-lineage-auditor.md` because the keyword-placement audit becomes part of the lineage report.

---

## Inputs

- `draft-voice-passed.md` (the cleaned article)
- `research-brief.md` §1 (the top 10 Ahrefs related terms (from matching-terms limit=10) with volume and KD)
- `structure_rules.md` §1.3, §1.4 (title and meta description rules)
- `content_rules.md` (voice — meta is brand-facing copy too, in the house voice)

---

## Process

### Step 1 — Meta title = the blog topic, as-is (v9: NO brand suffix)

- The title IS the article topic / H1, lightly tidied. **NEVER append "| Acme" or any brand suffix** (v9 change; the brand name is configurable via BRAND_NAME). No marketing construction, no "Buy Acme", no superlatives.
- **If the topic is a question, the title ends with "?"** (append it if the topic phrase omitted it).
- Example: topic "Does a Mechanical Keyboard Work With a Laptop" → title "Does a Mechanical Keyboard Work With a Laptop?" (no brand, "?" appended).
- If too long, trim the topic minimally (drop filler words like "for beginners"), never paraphrase or substitute words. Accuracy to the topic wins; length is a soft guide. The validator FAILs a title that contains the brand name, introduces a new word, or (for a question topic) lacks the "?".

### Step 2 — Meta description = synthesised from the top-5 competitors

This is the run-2 change. Don't write a description from scratch — study what Google already rewards:

1. Pull the meta description of each of the top-5 SERP results. Two sources, use whichever is available per URL:
   - The `<meta name="description">` tag from the competitor pages already fetched in research-flow sub-step 3 (Playwright/WebFetch).
   - The `snippet` field from SerpAPI's `organic_results` (research-flow sub-step 2) — this is what Google actually displays.
2. Read all 5. Identify what they have in common (the hook, the specific number, the framing Google favours for this query).
3. Write the BEST synthesis: clearest hook + one concrete fact + the primary keyword near the front. 140-160 chars.
4. **Fallback:** if competitor descriptions can't be extracted, derive a short description from the article's BLUF lede (first 1-2 sentences), trimmed to 140-160 chars.

Note in the output which path was used ("synthesised from top-5" vs "BLUF fallback").

### Step 3 — Build the slug

- All-lowercase, hyphen-separated
- Strip stopwords if URL gets long
- Match your site's existing pattern: `/keyboards/<topic>/`, `/desks/<topic>/`, etc. (the category paths are configurable per SITE_DOMAIN)
- Maximum 60 characters of slug after the category path

### Step 4 — Combined keyword table (placement + usage in ONE table, no KD)

One table only. Drop the KD column. Merge the placement audit and cluster-usage trace:

| Keyword | Vol | In title? | In meta? | In H1? | In first 100w? | In an H2? | Body uses |
|---|---|---|---|---|---|---|---|
| <primary> | 700 | yes (front) | yes | exact | sentence 1 | yes | ×4 |
| <variant 1> | 1,000 | — | — | — | — | yes | ×3 |
| <variant 2> | 350 | — | yes | — | — | — | ×1 |
| <variant 3> | 300 | — | — | — | — | — | ×1 |

For the primary keyword, all of title/meta/H1/first-100w/H2 should be "yes" (the SEO floor). At zero volume (no Ahrefs cluster), use the topic phrase as the single primary row and note "zero-volume: topic phrase used as keyword."

---

## Output

`seo-meta.md` with this structure:

```markdown
# SEO meta for: <topic>

## Meta block
| Asset | Value | Char count |
|---|---|---|
| Meta title | ... | ... |
| Meta description | ... | ... |
| Slug | ... | — |

## Primary keyword placement audit
[the 6-row table from Step 4]

## Cluster keyword usage trace
[the 4-row table from Step 5]
```

Also `seo-meta-status.json` with PASS / PARTIAL / FAIL + reasons.

---

## Hard checks

- **Meta title = the topic/H1, minimally trimmed, NO brand suffix, "?" if it's a question — NEVER reworded (v9).** Topic-fidelity wins over length. Drop only filler words; never paraphrase, substitute, or append a brand/CTA. Char window is a SOFT guide. No stray backslash. The validator FAILs a title that contains the brand name, introduces a new content word, or omits "?" on a question topic.
- **Every keyword in the placement audit must trace verbatim to a real pulled source in research-brief.md (v8 #62).** No synthesized keywords; an "Ahrefs"/"0 (Ahrefs)" annotation may be used only if the term truly came from Ahrefs. Add a "Source" column (Ahrefs / PAA / related-search / topic). The validator FAILs any audit keyword not found verbatim in the brief.
- Meta description 145-160 chars (hard fail outside)
- Primary keyword present in title AND meta description AND H1 AND first 100 words (each required)
- Slug all-lowercase, hyphenated, matches category path pattern
- At least 3 of 4 cluster keywords appear in body

---

## What it prevents

- Articles published with no meta title (defaults to H1, often too long, gets truncated)
- Meta descriptions Google rewrites because they're missing the primary keyword
- Mystery of "did we use the keywords we paid Ahrefs for" — now visible in QA block
- Hidden mismatch between target keyword and on-page optimisation

---

## Notes for the builder

- Char counts are pixel-accurate to Google's display limits. Don't relax these.
- The cluster keyword trace is the most useful audit for SEO leads — it answers "did the article optimise correctly" in one glance.
- If the primary keyword can't be naturally placed in all required positions, the H1 or topic is likely wrong, not the SEO meta. Flag for the team to revisit.
