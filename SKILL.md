---
name: geo-content-engine
description: End-to-end GEO content engine. Takes a topic and produces a research-grounded article engineered to get surfaced and cited in LLM answers. Runs nine phases (research, outline, draft, FAQ, internal linking, voice pass, SEO meta, lineage audit, score and deliver) and gates every draft through a run-halting anti-AI-writing check derived from Wikipedia's "Signs of AI writing" field guide (WP:AISIGNS): it FAILs em and en dashes, curly quotes, copula avoidance ("serves as", "boasts"), superficial "-ing" significance tails, weasel attribution ("experts say"), negative parallelism ("not X, but Y"), and significance or legacy puffery; and FLAGs rule-of-three, knowledge-cutoff disclaimers, and "Challenges/Future Prospects" closes. Reads bundled example canon files (content_rules, structure_rules, northstar) that you replace with your own brand rules. Output is a local Markdown file by default, with an optional Google Docs delivery add-on. Triggers on "run geo-content-engine", "generate an article for [topic]", "write a blog on [topic]", or explicit invocation as /geo-content-engine.
---

# geo-content-engine — research-grounded content + anti-AI-writing gate

> **What this is.** A production content pipeline that researches a topic against live SERP and AI-answer data, drafts an article grounded in that research, and refuses to ship it unless it passes a strict anti-AI-writing gate (`sub-skills/validate.py` + `sub-skills/style.json`, informed by Wikipedia's *Signs of AI writing*, `WP:AISIGNS`). It was built and battle-tested in production, generating hundreds of published articles. The `canon/` files are example rules; replace them with your own brand's.
>
> **v22 updates (2026-07-14):**
> 1. **Reddit → Arctic Shift.** The community-signal sub-step (research/01) now pulls real post + comment bodies from the Arctic Shift public archive API (no auth, not IP-blocked) instead of SerpAPI `site:reddit.com` snippets. The API requires a `subreddit` param alongside `query`; SerpAPI reddit snippets remain the automatic fallback if Arctic Shift is unreachable.
> 2. **Comparison tables.** Comparison topics (`X vs Y`, `difference between…`) now get exactly one research-sourced comparison table (planned in outline/02, written in draft/03), rendered as a real Doc table. **The facts come from research but every cell is written in Acme's own words — never copy a competitor's table verbatim (plagiarism/copyright).** The validator excludes table rows from the prose word-count and register checks (tables are structured data), while the anti-AI literal checks still apply.

End-to-end content engineering pipeline. The user invokes this skill with a topic. The skill runs the full pipeline internally (research, write, edit, score, deliver) and writes a finished article to a local Markdown file. An optional Google Docs delivery add-on lives in `optional/google-docs-delivery/`.

This is the single entry point. All nine internal phases are bundled inside this skill as reference instructions in `sub-skills/`. The example canon files are bundled in `canon/`.

---

## How this skill is organised

```
geo-content-engine/
├── SKILL.md                       ← this file (entry point)
├── README.md                      ← project overview + setup
├── .env.example                   ← copy to .env, add your own keys
├── sub-skills/
│   ├── 01-research-flow.md        ← read at phase 1
│   ├── 02-outline.md              ← read at phase 2
│   ├── 03-draft.md                ← read at phase 3
│   ├── 04-faq-builder.md          ← read at phase 4
│   ├── 05-internal-linking.md     ← read at phase 5
│   ├── 06-voice-pass.md           ← read at phase 6
│   ├── 07-seo-meta-builder.md     ← read at phase 7
│   ├── 08-data-lineage-auditor.md ← read at phase 8
│   ├── 09-score-and-deliver.md    ← read at phase 9
│   ├── validate.py                ← executable publish gate; voice-pass runs it (no self-grading)
│   ├── style.json                 ← editable banned words/phrases (the WP:AISIGNS anti-AI list)
│   ├── link_map.json              ← editable interlink map (pillars + secondary pools + service pools)
│   ├── length_target.py           ← SERP-driven length + coverage targets
│   └── lineage_check.py           ← research-to-draft lineage helper
├── canon/                         ← example canon; replace with your own brand rules
│   ├── content_rules.md           ← voice + the consolidated rule set
│   ├── structure_rules.md         ← page types + section types
│   └── northstar.md               ← scoring rubric
└── optional/
    └── google-docs-delivery/      ← optional add-on: publish the result as a Google Doc
```

The sub-skill files are NOT separately invokable skills (they have no separate YAML frontmatter that triggers Claude Code). They are **reference instructions** that this orchestrator reads at the right moment in the pipeline.

---

## Inputs the user provides

- **`topic`** (required) — the keyword or topic phrase, e.g., "what is waiting period in health insurance"
- **`vertical`** (optional) — health / car / bike / gmc / travel / life. If not provided, infer from the topic.
- **`restart_from_phase`** (optional) — number 1–9 to restart from a specific phase using already-generated artifacts. Used when team review comments demand a partial re-run.

---

## Pipeline execution

When invoked, follow this exact sequence. **Do not skip phases. Do not parallelise.** Each phase reads its instruction file from `sub-skills/`, executes those instructions, writes its output to the session folder, then proceeds.

### Setup (before phase 1)

1. **Slug rule (v20.6):** the session folder slug MUST be the full topic phrase, lowercased, with hyphens between words, no truncation. Example: topic "Does Group Health Insurance Cover Pre-Existing Conditions" -> slug "does-group-health-insurance-cover-pre-existing-conditions". Use the SAME slug across all runs of the same topic. No "compact" slug variants.

Create a session folder: `runs/<YYYY-MM-DD>-<slug-of-topic>/`
2. Note the start time, topic, vertical, and any `restart_from_phase` flag in `pipeline-status.json`
3. If `restart_from_phase` is set, jump directly to that phase — but verify all earlier-phase output files exist in the session folder; halt if any are missing.

### Phase 1 — Research

1. Read `sub-skills/01-research-flow.md` in full.
2. Execute the six sub-steps described there: Keyword + SERP intelligence (Ahrefs API v3, hardcoded token), PAA + zero-volume fallback (SerpAPI, hardcoded key), Competitor depth (WebFetch + Playwright), Community signal (Reddit JSON + WebSearch), Acme context + URL graph (WebSearch site:acme.com + optional GSC), and Data enrichment (citable stats).
3. Bundle the outputs into `research-brief.md` per the structure specified in the sub-skill file.
4. Write `research-execution.json` capturing PASS/FAIL/PARTIAL/SKIPPED status for each sub-step.
5. Halt if Sub-step 1 or 2 fails (no SERP data possible).

### Phase 2 — Outline

1. Read `sub-skills/02-outline.md` in full.
2. Read `canon/content_rules.md` and `canon/structure_rules.md`.
3. Build the MECE outline following the narrative spine (Orient → Understand → Decide → Close).
4. Plan the BLUF lede, the stage-setter, section-tool choices, FAQ themes, internal-link target phrases, Key Takeaways.
5. Write `outline.md` and `outline-status.json`.

### Phase 3 — Draft

1. Read `sub-skills/03-draft.md` in full.
2. Read `canon/content_rules.md` (the consolidated rule set (8 groups)) and the **v19 few-shot specimens** at the bottom of `sub-skills/03-draft.md` (tone calibration; `target_specimen.md` is retired).
3. Write the article body section by section, applying voice rules at write time.
4. Output `draft.md` (no FAQ yet) and `draft-status.json`.

### Phase 4 — FAQ

1. Read `sub-skills/04-faq-builder.md` in full.
2. Read `canon/content_rules.md` for FAQ rules.
3. Build the 4–6 FAQ block from real questions in `research-brief.md` §4.
4. Append the FAQ block to `draft.md` (between body and Key Takeaways).
5. Write `faq-builder-status.json`.

### Phase 5 — Internal linking

1. Read `sub-skills/05-internal-linking.md` in full.
2. Use `sub-skills/link_map.json` (pillar map + category secondary pools + service pools) plus `research-brief.md` §6.
3. Insert up to 3 links via the v21 3-slot structure (mandatory category pillar + category secondary + free topical), DRAFT-FIRST: link only noun phrases already in the prose; never hallucinate URLs, never force an anchor. Service-topic articles (challan/RTO/visa/ABHA…) use service pages and skip the insurance pillar.
4. Output `draft-linked.md` and `internal-linking-audit.json`.

### Phase 6 — Voice pass

1. Read `sub-skills/06-voice-pass.md` in full.
2. Read `canon/content_rules.md` (the consolidated rule set (8 groups)).
3. Run all eleven enforcement checks specified in the sub-skill file.
4. Output `draft-voice-passed.md`, `voice-pass-report.md`, and `voice-pass-status.json`.

### Phase 7 — SEO meta

1. Read `sub-skills/07-seo-meta-builder.md` in full.
2. Read `canon/structure_rules.md` for title and meta description rules.
3. Build meta title, meta description, slug. Audit keyword placement.
4. Output `seo-meta.md` and `seo-meta-status.json`.

### Phase 8 — Lineage audit

1. Read `sub-skills/08-data-lineage-auditor.md` in full.
2. Build the two audit tables — Execution Audit (every phase's status) and Lineage Audit (every research input traced to where it appears).
3. Output `audit-report.md` and `audit-status.json`.
4. **Hard gate:** any FAIL row without justification = halt the pipeline.

### Phase 9 — Score and deliver

**Phase 9 is gate-then-write.** The gate runs first; if it fails, nothing ships.

1. Read `sub-skills/09-score-and-deliver.md` for the QA block format.
2. **Step A — Run the gate (run-halting):**
   ```bash
   python3 sub-skills/validate.py runs/<run-id>/draft-voice-passed.md --json \
           --brief runs/<run-id>/research-brief.md \
           --seo runs/<run-id>/seo-meta.md \
           --run-folder runs/<run-id> \
           --corpus runs/<run-id>/competitor-1.md,runs/<run-id>/ai-mode.json --topic "<topic>" \
           --ai-mode runs/<run-id>/ai-mode.json \
           --audit runs/<run-id>/internal-linking-audit.json \
           --competitors runs/<run-id>/competitor-1.md,runs/<run-id>/competitor-2.md,runs/<run-id>/competitor-3.md,runs/<run-id>/competitor-4.md,runs/<run-id>/competitor-5.md
   ```
   - If exit code is non-zero, the run **HALTS** immediately. Print the FAIL list. Do NOT proceed. Fix the inputs and re-run from Step A.
3. **Step B — Deliver (default: local Markdown):** once the gate passes, assemble the article + QA block + footer and write it to `runs/<run-id>/final-doc.md`. That file is the deliverable.
4. **Optional Google Docs delivery:** to publish the result as a native Google Doc, use the add-on in `optional/google-docs-delivery/` (needs your own Google OAuth credentials; see that folder's README). It is not part of the default path.

### Wrap-up

1. Write final `pipeline-status.json` summarising all 9 phases.
2. Print the path to `final-doc.md`.

---

## Hard checks across the whole pipeline

These apply at the pipeline level. Phase-specific hard checks are inside each sub-skill file.

- **THE GATE IS RUN-HALTING (the most important rule).** `sub-skills/validate.py` is run with ALL inputs: `validate.py draft-voice-passed.md --brief research-brief.md --seo seo-meta.md`. If it exits non-zero (any FAIL), the pipeline **STOPS**: no `final-doc.md` is written, no "AUTO-APPROVE" is recorded, the run reports the FAILs and ends. A gate that the run can ignore is not a gate. FAIL = no delivery.
- **The pillar link is mandatory (configurable).** Phase 5 inserts up to 3 links via the 3-slot structure; `pillar_link` FAIL halts the run (service-topic articles are exempt, the validator skips the check). Every anchor must pass `anchor_quality`: a 2-6 word noun phrase already in the prose, sharing at least 2 nouns with its target slug.
- Input `topic` is non-empty.
- Every phase produces its expected output file before the next phase starts.
- Session folder is uniquely named (no overwrites).
- Every phase writes a `<phase>-status.json` file.
- Phase 8 (lineage audit) must pass before Phase 9 runs.
- Default delivery is a local Markdown file (`final-doc.md`). Google Docs is an optional add-on.

---

## What this pipeline prevents

- **Hallucinated SEO research** (Phase 1 reads from real Ahrefs/SerpAPI/GSC data, never the model's memory)
- **Drafts without a stage-setter or BLUF lede** (canon rules enforced at outline and draft phases)
- **Dramatic / copywriting register** (voice pass strips it; Rules #18–#27 written from team review)
- **Hallucinated Acme internal URLs** (every link traces to the team-verified `link_map.json`, to research-brief §6, or to a same-run WebSearch result — never a made-up path)
- **Scraped but unused research data** (lineage auditor catches this)
- **Silent phase skipping** (every phase writes status; lineage auditor consolidates)
- **LLM self-scoring leniency** (score-deflation guard in Phase 9)

---

## Environment requirements

Before invoking this skill, ensure:

- **API keys via environment.** Copy `.env.example` to `.env` and add your own `SERPAPI_KEY` and `AHREFS_API_TOKEN`. Load them before a run: `set -a; source .env; set +a`. Keys are read from `os.environ`, never hardcoded.
- **SerpAPI** (paid) powers SERP, PAA, AI Mode, Forums, News, Videos.
- **Ahrefs** (paid) powers related terms and question terms. Optional if you use the connected Ahrefs MCP tools instead of the REST API.
- **Playwright** installed locally: `pip install playwright && playwright install chromium`.
- **Python deps:** `pip install wordfreq textstat`.
- **GSC** and **Google Docs delivery** are both optional. GSC adds ranking-data context in research; the Google Docs add-on lives in `optional/google-docs-delivery/`.

---

## On failure

If any phase returns FAIL, halt the pipeline. Write `pipeline-failure.md` to the session folder naming the failed phase and its reason. Print the failure to the user. Do not proceed to subsequent phases.

The user can re-invoke with `restart_from_phase=<n>` once they've fixed the underlying issue (e.g., updated an env var, restored MCP connection).

---

## Notes for first-time invocation

- The first end-to-end run will likely surface 2–3 small bugs in the sub-skill instructions (typically path references or MCP method names). This is normal. Fix the offending sub-skill file and re-run.
- Suggested first test topic: **"what is waiting period in health insurance"**. The team has already validated a manual v3 output for this topic, so a clean pipeline run should produce comparable output.
- Expect ~3–5 minutes of LLM time per run on a typical topic. Most time is in Phase 1 (research, many MCP calls) and Phase 3 (drafting to the SERP-derived length — a guide topic can run ~2,000 words).

---

*This skill is the single entry point for the pipeline. Everything else inside this folder is reference material the orchestrator reads at runtime. To update the pipeline, edit the relevant `sub-skills/*.md` file or `canon/*.md` file. No changes to this SKILL.md needed.*
