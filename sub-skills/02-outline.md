---
name: outline
description: Build a MECE outline for a blog article applying the canon's narrative spine (Orient → Understand → Decide → Close), BLUF lede planning, stage-setter planning, question-format H2s (no word-count cap; full product name in every heading), and section-tool choices (prose, bullets, table, callout). v19 — section selection is driven by AI Mode weight × SERP frequency; Reddit/Quora are body content + FAQ supply only, never section creators. Reads content_rules.md and structure_rules.md. Use after research-flow.md and before draft.md. Triggers on "outline this article" or as part of the content-gen-pipeline.
---

# outline

Builds a structural plan for the article before any prose is written. Structure is cheaper to fix than prose; this is where most quality is won.

---

## When to use

Second stage of the pipeline, after `research-flow` produces `research-brief.md`. Output feeds `draft.md` which writes the actual prose.

---

## Inputs

- `research-brief.md` (from research-flow)
- `content_rules.md` (canon — voice + the consolidated rule set)
- `structure_rules.md` (canon — page types, section types, layout)

---

## Process

**v19 — section selection is driven by AI Mode weight × SERP frequency, not the union of competitor H2s.** AI Mode's answer shape decides section *size*; SERP frequency only adjusts up, never down to zero. The five cases:

| Signal | In SERP (top-10) | In AI Mode | What it becomes in our article |
|---|---|---|---|
| 1 | most URLs | yes (main block) | **Full section** (H2) |
| 2 | most URLs | yes, but as a bullet/sub-point | **One line / sub-point** inside a related section, not its own H2 |
| 3 | most URLs | not present | **Small mention / sub-point**, not a full section (SERP says it matters; AI Mode says it's not central) |
| 4 | not in SERP | yes | **Surfaced subtly inside an existing section**, not a section |
| 5 | not in SERP | not present | **Drop entirely** |

**Reddit/Quora/Forums are body content + FAQ supply only (v19).** They cannot create sections under any circumstance. A forum insight either: (a) maps to an existing section's topic → woven in as an example/edge case; (b) is a real user question → routed to faq-builder; (c) neither → dropped. The keyword test is **topic overlap**: does the insight's subject match any existing section's heading topic? If yes → goes there. If ambiguous or zero match → drop.

**Why this rule exists:** the union-of-competitors approach (v15-v18.1) made minor points into full sections — e.g. a minor spec appeared as one bullet in AI Mode and as a full H2 in our output. v19 pegs section *weight* to AI Mode's weighting, which is the cleanest single signal of what's central to the question vs. peripheral.

1. **Read research-brief.** Identify: target keyword, page type (transactional / informational / longtail per structure_rules.md §1.2), parent topic, competitor coverage, identified gaps.

2. **Pick the H1.** Must be the consumer question near-verbatim (content_rules.md Rule #1). For "what is a mechanical keyboard switch", H1 is "What is a mechanical keyboard switch?", not "Understanding Mechanical Keyboard Switches".

3. **Pick H2s using the v19 rule above** (AI Mode block → section; AI Mode bullet → sub-point; SERP-only → small mention; neither → drop). Headings are question-format, standalone, Title Case, full product name spelled out (no shorthand). **No word-count cap on headings** — clarity wins. Apply the narrative spine — Orient → Understand → Decide → Close. Each H2 corresponds to one phase or one move within a phase.

4. **Under each H2**, list:
    - The bullets / sub-points the section will cover (source these from research-brief)
    - The **section TOOL** choice (prose / bullets / table / callout / steps / comparison) with a one-line justification from content_rules.md §4
    - The opening angle: the reader question/decision this section opens on (NOT a bridge — bridges are retired, canon B4)

    **Section-tool rule of thumb (v22.4 — readers scan, they don't read):**
    - 3+ parallel items (symptoms, examples, conditions) → **bullet list**
    - a sequence the reader performs in order → **numbered steps**
    - 2+ things compared on the same attributes (add-on A vs add-on B, old vs new rule) → **small table** (2-3 columns; this is allowed on ANY topic — the v22 comparison-table mandate is only about *comparison-titled* topics, it does not forbid an earned table elsewhere)
    - one screenshot-worthy warning → **callout** (still max 1 per article)
    - everything else → prose

    **Variety guard: plan at most 2 consecutive prose-only sections.** If three sections in a row come out as pure prose, re-examine the middle one — one of them almost always contains a hidden list, sequence, or comparison. Do NOT invent a list where the content is genuinely one connected argument; the validator flags 3+ prose-only sections in a row (`structure_variety`, advisory) and a human decides. Prose is a choice, not a default.

5. **Plan the BLUF lede** (Rule #13). Sentence 1 IS the answer. Write the planned lede sentence.

6. **Plan the stage-setter** (Rule #9). 80-150 words between lede and first H2. Note the angle: who this article is for, what's at stake, why now.

7. **Plan callouts** (Rule #11). Maximum 1 earned callout per article. Identify the moment that meets the share-bar ("the reader would screenshot and send to a friend"). If no such moment exists, plan zero callouts.

8. **Plan the FAQ slot.** Specify the 4-6 question themes the faq-builder should source, drawn from research-brief §4. Do NOT pick exact questions yet; that's faq-builder's job.

9. **Plan internal-linking targets.** Identify 3-4 anchor phrases in the body where internal links would help. Do NOT resolve URLs; that's internal-linking's job.

10. **Plan Key Takeaways** (Rule #17). Terminal block, exactly 4 bullets with bold lead-ins (validator kt_exact). Note the angles (the article's payoffs reader walks away with).

11. **Comparison-table rule (v22) — MANDATORY on comparison topics.** If the topic is a comparison — the title contains `vs`, `versus`, `difference between`, `X or Y`, or `compare` (e.g. "membrane vs mechanical keyboard", "standing desk vs sit-stand converter", "linear vs tactile switches") — the outline MUST place **exactly one comparison table** in the section that contrasts the two options (usually the UNDERSTAND or DECIDE H2). Plan it here: name the two things compared and list the 5-8 rows (factors) the table will cover. Non-comparison topics plan no table.
    - **Provenance + anti-plagiarism (READ THIS):** the table's FACTS come from research (competitor scrapes + AI Mode + product specs), corroborated across sources where possible. **Write every cell in your brand's own words. NEVER copy a competitor's table, row, or sentence verbatim — facts are free to reuse, but their exact wording, selection, and arrangement are copyrighted. Verbatim copying is plagiarism and a duplicate-content risk.** Draft/03 writes the actual cells; here you only plan the factor rows.

---

## Output

`outline.md` with this exact structure:

```markdown
# Outline for: <topic>

## Page type and word count
<from structure_rules.md §1.2 — informational/transactional/longtail with target word count>

## H1
<the consumer question, near-verbatim>

## Lede (BLUF — sentence 1 IS the answer)
<the planned first sentence>

## Stage-setter (80-150 words)
<angle, stakes, who this is for>

## Body (narrative spine: Orient → Understand → Decide → Close)

### H2: <question, ≤10 words, Title Case> (ORIENT)
- Section tool: <prose|bullets|table|callout|steps> — <why>
- Covers: <bullet sub-points>
- Opens on: <the reader question/decision this section answers first>

### H2: <question, ≤10 words> (UNDERSTAND)
[same structure]

[... more H2s as needed, mapped to spine phases ...]

## Callout plan
<one earned callout location, or "none earned">

## FAQ themes (for faq-builder)
1. <theme — not exact question>
2. <theme>
[... 4-6 themes ...]

## Internal-link target phrases (for internal-linking)
1. <anchor phrase>
2. <anchor phrase>
[... 3-4 phrases ...]

## Key Takeaways plan
1. <angle 1 with bold lead-in>
2. <angle 2>
[... exactly 4 takeaways ...]
```

Also write `outline-status.json` with PASS / FAIL / PARTIAL + reason.

### v20.5: section-sources.json RETIRED

The v20.1 mandate to emit `section-sources.json` is REMOVED in v20.5. The heading-discipline check is now:

- **noun_floor** (validate.py): every meaningful noun in every H2 must appear in the raw scraped corpus (competitor-*.md + ai-mode.json). Mechanical grep, no agent claims.
- - **question_shape** (validate.py): every H2 must be a real question (starts with question word + ends with "?") or a How-to instruction.

The outline emits ONLY `outline.md` -- no per-H2 backing JSON. Source attribution is computed deterministically by the lineage auditor (`08-data-lineage-auditor.md`) at delivery time.


## Hard checks

- Every H2 maps to AI Mode (main block or sub-point) OR is a SERP-frequent topic surfaced as a sub-point — no H2 invented purely from competitor union
- No H2 contains a regulator/standards-body acronym
- No Reddit/Quora topic gets its own H2 — those route to FAQ or in-section detail only
- BLUF lede planned
- Stage-setter planned
- Section-tool choice justified for every H2 (no rote prose)
- At most 1 callout in the plan
- FAQ themes listed (4-6)
- Internal-link anchor phrases listed (3-4)
- Key Takeaways planned (exactly 4 bullets)
- Narrative spine phases assigned to every H2

---

## What it prevents

- Late-stage structural rework (always more expensive than outline rework)
- Section-tool monotony (everything as prose)
- Generic / non-MECE outlines that mirror competitor structure
- Forgotten stage-setter (a real v1 failure)
- Forgotten BLUF lede (a real v1 failure)

---

## Notes for the builder

- The outline is the highest-leverage stage. A bad outline can't be saved by a good drafter. A good outline can be saved by an average drafter. Invest in this skill more than draft.
- Cross-reference research-brief §5 (Information gain) when picking H2 themes — those are the gaps competitors leave that the article must fill.



## v20.7: Simple heading generation (NO polish loop, NO topic_anchor)

v20.6.3's Phase 2.5 polish loop is REMOVED. v20.6.2's topic_subject_presence rule is REMOVED. The heading approach is now:

### One prompt -- write H2s to the SERP coverage target

Read all `competitor-N.md` H2s, `ai-mode.json` text_blocks, AND `length-target.json` (v21). Write **as many H2s as the topic's coverage needs — aim for `section_target`** (the median competitor H2 count in `length-target.json`), between 3 and 9. A thin guide topic where competitors run 7+ sections needs 7+ sections; a simple topic needs 3-4. Cover every real sub-topic competitors + AI Mode cover that's relevant; do NOT invent sections to pad the count (noun_floor + topic_anchor still gate fabrication). Each H2 must meet these constraints (all enforced by validate.py + agent self-check):

1. Be a real question -- start with What/How/When/Why/Which/Can/Does/Is/Are/Will/Should and end with "?" (or be a "How to..." instruction)
2. Use the full product name exactly as written in H1 (no synonyms, no abbreviations)
3. Be 7-12 words
4. Be Grade 7-9 readability (plain English -- self-check, no FK enforcement)
5. Be distinct from H1 and from other H2s (no two H2s share the same opening 4 words; no exact H1 restatement)
6. Sound like a real reader's question, not a template
7. Keep the product name a CLEAN UNIT (v21): never weld a topic noun onto it ("Standing Desk Motor", "Standing Desk Memory Preset" are fabricated product names). Attach topic nouns with a preposition ("the motor in a standing desk", "memory presets in a standing desk") — and if that pushes the heading over 12 words, DROP the topic noun rather than weld it ("Can Two People Share the Same Standing Desk Setup?")

Pick concepts with strong support (multiple competitors + AI Mode blocks).

### Grammar self-check (ONE re-read pass)

Re-read each H2 aloud. Ask: does this parse as natural English? Any awkward verb pairing ("Are X Get", "Day-One Conditions")? Any templated pattern? If yes, REWRITE -- keep the concept, fix the grammar.

### What NOT to do

- Do NOT run 2-round polish loop
- Do NOT enforce topic_subject_presence (every H2 must contain "Mechanical" + "Switch")
- Do NOT enforce h2_synonym_drift, semantic_stack, redundant_abbreviation, h2_noun_stack, h2_readability, bluf_casing, body_casing
- Do NOT run regex relationship rules or LLM editorial second-pass

Trust the LLM with a clear prompt. validate.py enforces 5 sanity checks + anti-cheat (noun_floor). That's the architecture.

### Why simpler

v20.6.x stacked 87+ heading checks. Each was a guard against an LLM failure mode that often doesn't occur with a clear prompt. The over-correction caused templated H2s ("How Does X Affect the Y", "Are Switches Compatible"), semantic stacks (Day-One Conditions), and forced jargon. v20.7 strips to 5 checks. Verified on the headings-mini-v3 skill: 5 varied topics, all clean first-pass.
