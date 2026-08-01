---
name: score-and-deliver
description: Final stage of the Acme blog pipeline. Scores the draft against the 6-dimension northstar.md rubric, builds the QA block (including execution and lineage audits from data-lineage-auditor), and delivers the article as a Google Doc via the Google API Python Client (Docs + Drive APIs, OAuth). Reads northstar.md. Use as the last step of content-gen-pipeline. Triggers on "score and deliver" or as part of content-gen-pipeline.
---

# score-and-deliver

Final pipeline stage. Scores the article, generates the QA block, packages everything into a Word document, uploads to Google Drive where it converts to a Google Doc, and returns the link to the team.

---

## When to use

Last stage in the orchestrator. After `data-lineage-auditor.md`. Nothing should run after this.

---

## Inputs

- `draft-voice-passed.md` (the cleaned article body)
- `faq.md` (from faq-builder)
- `audit-report.md` (from data-lineage-auditor — execution + lineage tables)
- `seo-meta.md` (from seo-meta-builder)
- `northstar.md` (canon — 6-dimension scoring rubric)
- Google API Python Client + OAuth credentials (`credentials.json` / `token.json` at `~/.config/geo-content-engine/`, reused from the team's existing Sheet/Doc skills, with the `documents` scope added). See `REFERENCE-google-api-integration.md` in this folder. No separate Drive MCP.

---

## Process

### Step 1 — Score the draft against northstar

Read `northstar.md`. For each of the 6 dimensions, score the article on a 1-5 scale with one paragraph of written reasoning per dimension:

1. Consumer Question Clarity (weight 20%)
2. Content Depth & Usefulness (weight 20%)
3. Structure & Scannability (weight 15%)
4. Brand Voice & Publishability (weight 15%)
5. Replaceability (weight 15%)
6. Design & Visual Execution (weight 15%)

Compute the weighted average: `weighted = sum(score_i * weight_i)`.

### Step 2 — Score-deflation guard (anti-leniency)

If the LLM critic scored 5/5 on 5 or more dimensions AND the article has any of these known weak signals, automatically deflate the relevant dimension by 1 notch:

- Body below the SERP-derived band in `length-target.json` (length_vs_serp FLAG) OR fewer H2 sections than `section_target` (coverage_vs_serp FLAG) → deflate "Content Depth" (thin for the topic)
- 4+ consecutive prose paragraphs flagged by voice-pass → deflate "Structure & Scannability"
- Any forbidden-phrase pattern flagged by voice-pass → deflate "Brand Voice"
- Any FAIL or SKIPPED-without-substitute in the execution audit → deflate "Replaceability"

This guard exists because LLM self-scoring is generous. v2's self-score was 4.70; team review revealed it was closer to 4.0.

### Step 3 — Verdict

- Weighted ≥ 4.0 AND no dim < 3 → AUTO-APPROVE
- Weighted ≥ 3.5 AND no dim < 2 → CONDITIONAL (publish after light edit)
- Anything else → REJECT (regenerate or restart from the failing stage)

*(Step 4, the GPTZero smell test, was removed in v22.3 — team decision: GPTZero will not be used. AI-likelihood is covered by the validator's ai_* gates + the ai_proposed_tells pilot.)*

### Step 5 — Build the QA block (v21 — ONE format only)

Build the QA block in the **v20.6.2 STRICT format defined at the end of this file**: exactly three sections — SEO Meta, Research Provenance, Heading Source — under the "🔖 DELETE BEFORE PUBLISHING" header. Nothing else. No Verdict, no Quality Scorecard, no Readability, no Voice & Canon section (all removed in v20.5; the validator catches what they reported). The Heading Source table is built from `heading-sources.json` (computed by the lineage auditor, never author-claimed).

*(v21 cleanup: the v20.3 two-section test format and the old six-section production spec that used to sit here were removed — three stacked formats in one file caused format drift. The strict format at the end of this file is the only spec.)*

### Step 6 — Deliver

**Default delivery is a local Markdown file.** The article is already Markdown, so once the gate (`validate.py`) passes, assemble the QA block + article + footer and write the result to `runs/<run-id>/final-doc.md`. That file is the deliverable. No external service, no auth. This is the default path and needs nothing beyond the repo.

**Everything below in this Step 6 is the OPTIONAL Google Docs add-on** (`optional/google-docs-delivery/`). Use it only if you want the result published as a native Google Doc; it needs your own Google OAuth credentials. Script paths below are under `optional/google-docs-delivery/`.

Use the Google API Python Client with OAuth, not a Drive MCP and not a hand-built .docx.

**Auth (reuse the team's existing credentials):**
- Packages: `google-api-python-client google-auth google-auth-oauthlib`
- Credentials: reuse the existing `credentials.json` / `token.json` at `~/.config/geo-content-engine/` (same `authenticate()` pattern as the Sheets skill).
- **Scope change:** this skill writes a Doc, so add `https://www.googleapis.com/auth/documents` to the existing scopes (`drive.file`, `spreadsheets`). Per the team guide's gotcha #2, **after adding the scope you must delete `token.json` once and re-auth** so the new token carries the documents scope.

**Create + populate the Doc:**
1. Create a native Google Doc via the Drive API:
   `drive.files().create(body={'name': 'Acme Blog v<N> — <topic>', 'mimeType': 'application/vnd.google-apps.document'}, fields='id')`
2. Build a Docs API `batchUpdate` request list to insert content with formatting (named styles HEADING_1/HEADING_2 for H1/H2, bold runs, bulleted lists, and tables via `insertTable`). Order:
   - "🔖 DELETE BEFORE PUBLISHING" header
   - QA block (with its tables)
   - separator
   - article body (H1, lede, any stage-setter, H2 sections with correct section tools)
   - a clear visual separator (horizontal rule or spaced heading) BEFORE the FAQ
   - FAQ block — rendered as a real **numbered list** (canon Rule #46): each item is a numbered paragraph with the question bold, the answer in the paragraph beneath it. Never render the FAQ as plain bold lines.
   - a clear visual separator BEFORE Key Takeaways
   - Key Takeaways (terminal, as a bulleted list with bold lead-ins)
   - a short, explicit "Next step" CTA line (one sentence pointing to the relevant Acme action/page — clear, not "click here")
   - IRDAI registration footer (with the data-currency note, e.g. "Information current as of May 2026; figures cited are FY24")
   - Do NOT render the draft's "Team to supply" appendix into the published Doc body — it is internal; if present, place it under the QA block, not in the article.
3. **Convert links to REAL Doc hyperlinks AND strip the markdown brackets (run-1 + run-2 fix).** Markdown link syntax does NOT auto-render in Google Docs, and the run-2 bug left literal `[ ]` brackets showing. For every link:
   - Insert only the visible anchor text (e.g., "survival period" or the publisher name "IRDAI"), with the surrounding `[` `]` and `(...)` markdown REMOVED. The brackets must not appear in the final Doc text.
   - Then apply a hyperlink to that text range with an `updateTextStyle` request: `{'updateTextStyle': {'range': {'startIndex': s, 'endIndex': e}, 'textStyle': {'link': {'url': '<url>'}}, 'fields': 'link'}}`.
   - This applies to BOTH internal Acme links AND source citations. A source citation renders as "Source: IRDAI" where the word "IRDAI" carries the link — never `[IRDAI]` with brackets, never a merged label like "[Business Standard / IRDAI]" (one publisher only, per canon Rule #44), never a bare label with no URL.
   - After building, scan the assembled Doc text for any surviving `[` or `]` characters in body/citation runs; if found, the bracket-strip failed — fix before returning the link.
4. Run `docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests})`.

**RUN `optional/google-docs-delivery/build_doc.py` as the delivery step — do NOT hand-write the batchUpdate (v11 fix).** Format kept drifting because delivery was improvised prose. build_doc is the EXECUTED renderer: it parses the assembled markdown into typed blocks (Title-Casing H1/H2 incl. acronyms like "Non-PPN", stripping every `[ ]`/`\`, building tables from structured cells so a `| Acme` value never splits), then renders the Doc with the locked `docbuild.FORMAT` (in the optional add-on) (Arial 11, Heading 1-4 named styles, grey `#666666` explainers, pageless, fixed meta + keyword table widths, callout style). Call:
```bash
python3 optional/google-docs-delivery/build_doc.py runs/<run-id>/final-doc.md --title "Acme Blog — <topic>"
# verify first with --dry-run to confirm the block structure + zero surviving brackets
```
The meta and keyword tables are built by passing STRUCTURED cell arrays to `docbuild.build_table(rows)` — never as a markdown pipe-string (that's what split the `| Acme` cell). build_doc ends with `assert_no_brackets()` and must hard-stop if any bracket survives.

**POST-DELIVERY CHECK (v13, publish-blocking) — the gap that let the broken v12 doc ship "AUTO-APPROVE".** After rendering, read the delivered Doc BACK and run `verify_rendered_docx()` (or the same checks on the Google Doc text via the API): it FAILs on raw `|` pipes, literal `**`, surviving `[ ]` brackets, `|---|` separator rows, or "scorecard present but zero real tables." If it fails, the render is broken — do NOT return the link or mark AUTO-APPROVE; rebuild. Nothing inspected the *delivered* artifact before v13; this closes it. (Local proof without OAuth: `python3 optional/google-docs-delivery/build_doc.py final-doc.md --docx test.docx` then open it.) NOTE: the Google Docs API render needs the team's OAuth (token.json with the `documents` scope) and one confirmation run; the parsing/format logic is unit-tested (`python3 optional/google-docs-delivery/build_doc.py --selftest`).

**Underlying helpers in `optional/google-docs-delivery/docbuild.py` (build_doc imports these):**
- `from docbuild import FORMAT, parse_links, build_table, assert_no_brackets`
- **`FORMAT`** is the single fixed style spec — apply it identically every run: `body_font`/`body_size` (Arial 11), `h1_size`/`h2_size`, paragraph spacing, `meta_table_widths` and `keyword_table_widths` (wide Keyword column, narrow yes/no columns — fixes the cramped column), and the `callout` style. Never invent fonts/sizes/widths per run.
- **`parse_links(text)`** → returns clean text (every `[ ]` and `\` removed) plus link ranges to apply with `updateTextStyle`. This is how citations and internal links render: anchor text only, brackets stripped, hyperlink applied. It fixes the surviving-bracket bug at the source.
- **`build_table(rows)`** → pass STRUCTURED cell data (a list of rows, each a list of cell strings); it never splits on `|`, so a meta-title value like "What is waiting period? | Acme" stays in one cell and ragged rows are padded so columns can't shift. Build the meta table and the keyword table this way — never from a markdown pipe string.
- After assembling the Doc text, call **`assert_no_brackets(full_text)`** as a post-build guard; if any `[`, `]`, or `\` survived, fix and rebuild before returning the link.
- **Callouts** (e.g. "⚠️ The 60-month moratorium rule:") render as a styled standout block per `FORMAT['callout']` — a single-cell shaded table (background `#FFF4CE`, the ⚠️ + bold lead-in retained), NOT a plain paragraph, so they visibly stand out.
- **Set the document to PAGELESS (v9).** Apply pageless mode via the Docs API `documentStyle` so wide QA tables (the 8-column keyword audit) aren't crushed into page margins. Pageless fixes the cramping; the structured `build_table` fixes the cell structure — do both. If the API can't toggle pageless programmatically, note it for a one-time manual setting.
- **All headings in Title Case (v9, canon B2):** before inserting, normalise every H1/H2 to Title Case (capitalise principal words; keep short connectors — of, in, the, and, are, to — lowercase unless first/last; leave acronyms like IRDAI/PED/NCB uppercase). The validator `title_case` check confirms it.

**Formatting quality (run-1 was 2/10 — fix this).** The Doc must be clean and aligned, not a wall of text:
- Use real named paragraph styles: `HEADING_1` for the article H1 and QA section titles, `HEADING_2` for H2s. Never fake headings with bold text.
- Add paragraph spacing: `spaceAbove`/`spaceBelow` ~6-10pt on body paragraphs, more before headings. No paragraphs jammed together.
- Tables: use `insertTable`, bold the header row, give every column consistent width, and keep cell text single-line where possible. Never paste a markdown `| a | b |` string as text — build an actual table.
- The QA-block section explainers render as italic, smaller (or grey) text directly under each section title.
- One blank paragraph between sections. Consistent bullet style for lists.
- Verify: after building, the Doc should look like a designed brief, not a text dump. If a table renders as raw pipes or a heading renders as plain bold, the formatting step failed — rebuild it.
4. URL: `https://docs.google.com/document/d/<doc_id>/edit`

### Step 7 — Return the Doc link

Return the Google Doc URL to the orchestrator. The orchestrator prints it to the user.

---

## Output

- A Google Doc with the article, formatted, and QA block on top
- A Doc URL returned to the caller
- `score.md` saved to the session folder (the score breakdown for record-keeping)
- `score-and-deliver-status.json` with PASS / FAIL

---

## Hard checks (publish-blocking)

- Northstar weighted score must be computed (no skipping the score step)
- Execution audit must have zero FAIL rows without justification (else REJECT regardless of score)
- Lineage audit must have zero "Not used + no justification" rows
- **`sub-skills/validate.py` must return `overall: PASS` on the final article. Any FAIL → REJECT regardless of the northstar score (the validator is the deterministic publish gate).**
- The Google Doc must contain all required sections (article + FAQ + KT + Next-step CTA + IRDAI footer)
- FAQ rendered as a numbered list (canon Rule #46)
- Zero literal `[` or `]` brackets surviving in body or citation text (run-2 bug)
- Every source citation is single-publisher and hyperlinked (no merged labels, no bare labels)
- Exactly one pillar interlink to `acme.com/<vertical>/` present in the body
- The "Team to supply" appendix is NOT rendered into the article body
- The Google Docs API call must succeed (else FAIL with a retry recommendation)

---

## What it prevents

- Publishing below the northstar bar
- Publishing without an audit trail
- Score-inflation by the LLM critic (the deflation guard is the safeguard)
- Lost runs (everything is in the Drive Doc; the session folder is a backup)

---

## Notes for the builder

- The deflation guard in Step 2 is the most operationally important detail. Without it, the LLM self-scores will drift generous over time. Test this guard against known-bad articles (an old v1 with the 40% fabricated stat) — it should deflate Content Depth to 3 or below.
- The Docs API can fail on first call if the token lacks the `documents` scope (delete `token.json` and re-auth once) or on transient network errors. Implement a single retry with 5-second bacmeff before failing hard.
- This skill produces the artifact the team sees. Get the QA block formatting right. Headings, tables, separators must all render cleanly in the Google Doc.


## v20.5 QA Block (publish-time, deletable header)

```markdown
# 🔖 DELETE BEFORE PUBLISHING — QA Block

## Section 1. SEO Meta

| Field | Value |
|---|---|
| Meta title (50-60 chars) | <title> |
| Meta description (145-160 chars) | <desc> |
| Slug | <slug> |
| Primary keyword | <kw> |
| Primary keyword placement | title/H1/first-100w/meta/slug/H2 (yes/no per slot) |

## Section 2. Research Provenance

| Source | Pulled | Used in article | Used in FAQ | Status |
|---|---|---|---|---|
| Competitor H2s | <count> | <yes/no> | -- | -- |
| AI Mode blocks | <count> | <yes/no> | -- | -- |
| Reddit threads | <count> | <count> | <count> | -- |
| Quora questions | <count> | -- | <count> | -- |
| PAA | <count> | -- | <count> | -- |
| Ahrefs related terms (limit=10) | 10 | <count placed in body> | -- | -- |
| Ahrefs question terms (limit=10) | 10 | -- | <count placed in FAQ> | -- |

## Section 3. Heading Source (NEW in v20.5)

| H2 | Source URLs / AI Mode blocks |
|---|---|
| <H2 #1> | competitor-A.com (H2: "..."), ai-mode: "Block Title" |
| <H2 #2> | competitor-B.com (H2: "..."), competitor-C.com (H2: "...") |

(Built deterministically from `heading-sources.json` -- not author-claimed.)
```

That's it. Verdict, Quality Scorecard, Readability, Voice & Canon sections are REMOVED in v20.5 -- they were noise. Validator catches the rest.



## v20.6.2 STRICT QA BLOCK FORMAT (CRITICAL — do not deviate)

The QA Block has EXACTLY THREE sections. No verdict block, no quality scorecard, no readability section, no voice & canon section. If you find yourself writing any of those, STOP — they were removed in v20.5.

Required structure:

```markdown
# 🔖 DELETE BEFORE PUBLISHING — QA Block

## Section 1. SEO Meta
| Field | Value | ... |

## Section 2. Research Provenance
| Source | Pulled | Used in article | ... |

## Section 3. Heading Source
| H2 | Source URLs / AI Mode blocks |
```

That is the complete QA Block. Nothing more. Generating Verdict / Quality Scorecard / Readability / Voice & Canon sections is a REGRESSION to v20.4 — do not do it.

