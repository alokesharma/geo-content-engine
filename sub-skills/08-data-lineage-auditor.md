---
name: data-lineage-auditor
description: Two-part audit for a pipeline run. Execution Audit (every research and generate step gets PASS/FAIL/PARTIAL/SKIPPED status with a reason). Lineage Audit (every research input traced to where it appears in the article, or justified as not used). Outputs audit-report.md which score-and-deliver consumes to populate the QA block on the final Google Doc. Use after seo-meta-builder and before score-and-deliver. Triggers on "audit pipeline" or as part of content-gen-pipeline.
---

# data-lineage-auditor

The single source of truth for "did the system run correctly". Surfaces what ran, what failed, what was skipped, and proves every research input was either used in the article or explicitly justified as not used.

This skill exists because the v1/v2 runs scraped Reddit/Quora/PAA but never used the signal in the article. The lineage audit makes that failure mode visible in the QA block.

---

## When to use

After `seo-meta-builder.md`. Before `score-and-deliver.md`. The audit report becomes part of the QA block at the top of the final Google Doc.

---

## Inputs

- `research-brief.md` (the input lineage source)
- `research-execution.json` (status log from research-flow)
- Every Generate-stage status file: `outline-status.json`, `draft-status.json`, `faq-builder-status.json`, `internal-linking-audit.json`, `voice-pass-status.json`, `seo-meta-status.json`
- `draft-voice-passed.md` (the final article — needed for lineage tracing)
- `seo-meta.md` (the SEO meta + keyword trace already done by seo-meta-builder)
- `internal-linking-audit.json` (already has its own audit; this skill consolidates)

---

## Process

Produce ONE merged "Research Provenance" table (run-2 change — the old separate Execution and Lineage tables felt redundant to readers). Each row collapses three facts into one line: what source, what we pulled from it (with counts), and where it landed in the article. The status is implied by the counts.

Read every research source from `research-brief.md` plus the per-step status JSONs. Build this single table — counts are mandatory (this is the team's proof the article is research-backed):

```markdown
## Research Provenance — proof this article is built on real fetched data, not LLM guesswork

| Source | What we pulled | Where it's used |
|---|---|---|
| Ahrefs keywords | 4 keywords (primary 700 vol) | H1, meta, body |
| Ahrefs questions report | 12 questions | 3 → FAQ |
| SERP URLs (Ahrefs/SerpAPI) | top 10 ranked | 5 read deeply |
| Competitor deep reads | 5 of 5 (Competitor A, Competitor B, Competitor C, …) | scaffolding + gap analysis |
| PAA box (SerpAPI) | 4 questions | 1 → FAQ, 1 → body |
| Reddit threads (search.json) | 3 threads, 18 comments read | 2 insights → body/FAQ |
| Quora titles | 10 question titles | 3 → FAQ |
| Third-party research data | 5 stats (each with source + date) | all cited inline |
| Primary-source citations | 3 (official standard, May 2024, …) | body |
| Brand internal-link URLs | 13 found | 4 linked |
| Brand internal DATA | [needed — team to supply] | flagged, not yet used |
```

Rules for the table:
- **Every row carries a count.** "5 of 5 read", "3 threads, 18 comments", "5 stats" — counts are what give the team confidence. A row with no number is a fail.
- If a source returned nothing (e.g., Reddit genuinely empty), the row says so with the substitute: "Reddit | 0 threads (search.json) | substitute: Quora + PAA carry community signal".
- If a competitor read failed and backfill kicked in, reflect it: "Competitor deep reads | 5 of 5 (3 top + 2 backfill; #4/#5 hard-blocked)".
- The `[brand internal data needed]` flag row stays visible so the team sees what would strengthen the piece.

For lineage, check each source by string-matching the article body. Use loose matching (don't require exact paraphrase) but require the source's core fact or angle to be traceable.

### Executable provenance (v8, #57 — stop self-reported "usage" claims)

The provenance table was previously prose the model filled in, so it could *claim* "Reddit → FAQ Q3" without it being true (the original v1/v2 failure mode). Make it executable: for each pulled item in `research-brief.md` (§4.2 Reddit, §4.3 Quora, §4.4 PAA, §7 stats) AND the raw `reddit-*.json` / `quora-titles.json` in the run folder, string-match its key phrase/number against `draft-voice-passed.md`. Produce real counts — pulled vs found-in-article vs genuinely-unused — and for each "used" claim, record the matched sentence. A row that claims "used" but whose phrase/number is NOT found in the article = FAIL (the table is overclaiming). Keyword provenance is already enforced by `validate.py` (`--brief` keyword_trace, #62); apply the same string-match principle to community + stat sources here. Never write "→ used" without a located match.

---

## Output

`audit-report.md` — contains the single Research Provenance table (score-and-deliver renders it as QA Section 5).

`audit-status.json`:

```json
{
  "skill": "data-lineage-auditor",
  "status": "PASS" | "PARTIAL" | "FAIL",
  "provenance": {
    "total_sources": <n>,
    "with_counts": <n>,
    "used": <n>,
    "substituted": <n>,
    "skipped_with_substitute": <n>,
    "unused_no_justification": <n>,
    "brand_internal_data_flags": <n>
  }
}
```

(Internally the skill still verifies both that each step ran AND that each source landed — but it reports them as one provenance table, not two.)

---

## Hard checks (publish-blocking)

- Every step in the expected pipeline has a status row. Missing rows = hard fail.
- Zero FAIL statuses, OR every FAIL has an explicit documented justification.
- Zero SKIPPED statuses without a named substitute.
- Zero data sources with "not used and no justification".

---

## What it prevents

- Silent step skipping (the v1/v2 Reddit/Quora failure mode the team explicitly flagged)
- Data scraped but not used (lineage failure)
- QA block looking complete when it isn't
- "Pipeline ran" being claimed without proof of which sources contributed

---

## Notes for the builder

- This skill is the operational backbone of trust in the pipeline. If this skill is weak, the whole system loses credibility with the team.
- The status of each upstream skill is read from THAT skill's status JSON. This auditor never re-derives status; it only consolidates and validates.
- The lineage check uses string matching. False negatives (article uses the fact but in different phrasing) are common; lean toward generous matching, flagging only clear misses.
- This skill is what made the team's "non-negotiable QA proof" requirement actually enforceable.


## v20.5: Heading Source computation (NEW)

After lineage audit completes, write a deterministic "Heading Source" table to `heading-sources.json`. This table is consumed by Phase 9 for the QA Block. **Computed by code, not the agent** -- prevents fabricated source claims.

Algorithm:

1. Load each `competitor-N.md` and pull the H2 list per competitor.
2. Load `ai-mode.json` and pull every `text_block` title + bullet headings.
3. For each final article H2 (from `draft-voice-passed.md`):
   - Extract H2 noun-set (lowercased, stopwords stripped, >3 chars).
   - For each competitor H2: if noun-overlap with the article H2 is >=50% (|H2 ∩ competitor_H2| / |H2|), record that competitor + the competitor's H2 string verbatim.
   - For each AI Mode block: if noun-overlap >=50%, record `ai-mode: <block_title>` as a source.
4. Emit `heading-sources.json`:

```json
{
  "headings": [
    {
      "h2": "How do I set up a standing desk for the first time?",
      "sources": [
        {"competitor": "Competitor A", "url": "...", "h2": "How do you assemble a standing desk?"},
        {"competitor": "Competitor B", "url": "...", "h2": "Standing Desk First-Time Setup"},
        {"competitor": "ai-mode", "block": "Standing Desk Setup"}
      ]
    },
    ...
  ]
}
```

If a final H2 has ZERO sources at >=50% overlap → that's a quiet flag (record in audit) but not a halt -- the validator's `topic_anchor` + `noun_floor` already gate fabrication; this table is for transparency, not enforcement.

Add lineage rows for the new Ahrefs sources (related terms + question terms) so the team can see how Ahrefs feeds the article.
