---
name: faq-builder
description: Build a 4-6 question FAQ section for a blog article using real user questions sourced from Ahrefs matching-terms, Reddit thread titles, Quora question titles, and SERP PAA box. Rewrites raw user phrasing into blog-ready questions and writes 30-60 word answers per FAQ. Use this skill whenever the article needs an FAQ block, typically after the article body is drafted. Triggers on phrases like "build FAQ", "add FAQ section", "FAQ for this article", or as part of the content-gen-pipeline orchestrator.
---

# faq-builder

Builds the FAQ block for a blog article. Sources real user questions, rewrites them into clean blog format, writes tight 30-60 word answers, and outputs a markdown FAQ section ready to slot into the draft.

This skill exists because every v1 of an article had two FAQ failures: (1) questions were paraphrased from the model's training memory rather than real search data, and (2) answers were too long and copy-pasted body content. This skill fixes both by mandating real question sources and capping answer length.

---

## When to use

Invoke this skill **after** the article body draft is written and **before** `voice-pass.md` runs. The article body must exist so the FAQ skill can verify the AEO rule (FAQ answers must phrase the same fact differently from the body — same SEO benefit, no duplicate-content penalty).

Do NOT use this skill standalone outside the pipeline. The skill assumes a session folder structure (`runs/<run-id>/`) and depends on `research-brief.md` being present.

---

## Inputs

This skill reads four files from the current session folder:

1. **`research-brief.md`** — must contain populated `§4.1 Ahrefs matching-terms`, `§4.2 Reddit threads`, `§4.3 Quora question titles`, and `§4.4 SERP PAA` sections. If any of these sections is empty, the skill records that source as "SKIPPED" in its status JSON and proceeds with the remaining sources.

2. **`draft.md`** — the article body written by the `draft.md` skill. Read to identify what topics the body already covers (so the FAQ can phrase the same facts in different language per the AEO rule).

3. **`content_rules.md`** (shared MD) — read §FAQ rules (the canon's rules on FAQ shaping). Specifically: FAQ answer length 150-300 characters (BLUF: first sentence answers the question) (per Rule #22), no regulatory minutiae (Rule #23), AEO-fresh-phrasing rule.

4. **`research-brief.md` §4** — the four question sources listed above.

---

## Process

### Step 1 — Build the candidate pool

Collect every available question from the four sources. Tag each by source.

| Source | Where to read from | Tagged as |
|---|---|---|
| Ahrefs matching-terms with terms=questions (limit=10) | `ahrefs-questions.json` | `ahrefs` |
| Reddit thread titles | `research-brief.md` §4.2 | `reddit` |
| Quora question titles | `research-brief.md` §4.3 | `quora` |
| SERP PAA box | `research-brief.md` §4.4 | `paa` |
| Google Forums threads/questions (v12) | `research-brief.md` §4.5 | `forums` |
| Google Videos transcript questions (v12) | `research-brief.md` §4.6 | `video` |

Output of this step: an internal list of (question_text, source_tag, signal_score) tuples.

### Step 2 — Deduplicate by intent

Many questions across sources are paraphrases of the same intent. Group them. For each cluster of paraphrases, keep the single best phrasing (preference order: PAA > Reddit > Quora > Ahrefs, because PAA reflects what Google already surfaces and Reddit/Quora reflect real user language).

Example cluster:
- ahrefs: "what is actuation force on a mechanical switch"
- paa: "What is actuation force on a keyboard switch?"
- reddit: "How heavy is the press on a linear switch?"

Keep one: "What is actuation force on a mechanical keyboard switch?" (rephrased to combine specificity from Reddit + clarity from PAA).

### Step 3 — Score and rank

For each remaining (deduplicated) question, compute a signal score:

- +3 if the question appears in 2+ sources (cross-source signal)
- +2 if the question is from PAA (Google has chosen to surface it)
- +1 if the question is from Reddit (real user pain point)
- +1 if the question has a specific edge case the body didn't fully cover (e.g., "what if my board isn't hot-swap" — addresses compatibility)
- −2 if the question's answer would duplicate the body's main argument

Sort descending by score. Take top 4-6.

### Step 4 — Rewrite to blog-ready phrasing

For each selected question, rewrite the raw user phrasing into a clean blog question. Apply these rules:

- ≤12 words
- Sentence-case, ends with question mark
- Strip filler ("hey guys", "does anyone know", typos, multiple question marks)
- Preserve the user's actual intent and everyday idioms
- No marketing language ("best", "cheapest", "guaranteed")

Examples:
- RAW: "hey do the keys still work after i swap switches???" → CLEAN: "Do the keys still work after you swap the switches?"
- RAW: "what is ped—i mean actuation force on switches" → CLEAN: "What is actuation force on a mechanical keyboard switch?"

### Step 5 — Write answers (150-300 characters (BLUF: first sentence answers the question) each)

For each question:

- Word count: 150-300 characters (BLUF: first sentence answers the question). Hard limit. Anything longer belongs in the body.
- Self-contained: makes sense without re-reading the question
- Specific: includes a number from `research-brief.md` where available; hedge with "typically" / "in most plans" when no specific number exists
- AEO-fresh: different sentence structure AND at least one different specific (number, example, or angle) compared to the body's coverage of the same fact. Same SEO benefit (FAQ schema still fires); no duplicate-content penalty.
- No regulatory citations inside answers. If the body cites a regulator or standards body's clauses, the FAQ may reference that source by name only, not by clause/circular number (per content_rules.md Rule #23).
- No forbidden phrases (read the FORBIDDEN_PHRASES list from `content_rules.md`)

### Step 6 — Order the FAQ

Order: most-asked first (by signal score), edge cases later. Always end with a calm clarifier (e.g., "Do switches come pre-lubed out of the box?") rather than a high-anxiety question. This keeps the article on a measured close before Key Takeaways.

### Step 7 — Write output

Output is a markdown file at `runs/<run-id>/faq.md`. **FAQs are a NUMBERED list (canon Rule #46)** — not bullets, not bold-question-only. Use this exact structure:

```markdown
## Frequently asked questions

1. **[Question 1]?**
   [Answer 1, 150-300 characters (BLUF: first sentence answers the question).]

2. **[Question 2]?**
   [Answer 2, 150-300 characters (BLUF: first sentence answers the question).]

[... 3-5 more, continuing the numbering]
```

The delivery step (`score-and-deliver`) renders this as an actual numbered list in the Google Doc, with each question bold and its answer in the following paragraph.

Also write `runs/<run-id>/faq-builder-status.json` with:

```json
{
  "skill": "faq-builder",
  "status": "PASS" | "PARTIAL" | "FAIL",
  "reason": "...",
  "sources_used": {
    "ahrefs": <count of ahrefs questions in final FAQ>,
    "reddit": <count>,
    "quora": <count>,
    "paa": <count>
  },
  "faq_count": <total questions in output, must be in [4, 6]>,
  "answer_word_count_min": <int>,
  "answer_word_count_max": <int>
}
```

The orchestrator and `data-lineage-auditor.md` will consume this status file later.

---

## Hard checks (skill will not pass these are not satisfied)

- FAQ count: 4-6 questions. Reject runs that produce <4 or >6.
- **Output is a numbered list (1., 2., 3., …), not bullets (canon Rule #46).**
- Every question ≤12 words.
- Every answer 150-300 characters (BLUF: first sentence answers the question). Anything outside the band = hard fail; rewrite that specific answer.
- No question repeats a question already addressed verbatim in an article H2.
- No answer copy-pastes a sentence from the body (similarity check: <40% n-gram overlap).
- No forbidden phrases (FORBIDDEN_PHRASES list from `content_rules.md`).
- No regulatory document/circular numbers in answers.
- At least one community-sourced question (Reddit OR Quora OR PAA) if any of those sources had data in research-brief. If all three were empty in the brief, this check is skipped but a warning is logged.

---

## What it prevents

- **Lazy FAQ** — paraphrased from the model's memory rather than real search data
- **Long, body-duplicating answers** — wastes the AEO opportunity, hurts page quality signals
- **Missed community signal** — the v1/v2 failure where Reddit/Quora were pulled in research but not used. This skill's "at least one community-sourced question" hard check is exactly this safeguard.
- **Regulatory creep** — FAQs reading like compliance documents instead of plain answers

---

## Example output

For the topic "what is a mechanical keyboard switch":

```markdown
## Frequently asked questions

1. **What is the difference between a linear and a tactile switch?**
   A linear switch presses down smoothly with no bump. A tactile switch gives a small bump partway down so you can feel the moment the key registers, without any added click sound.

2. **Which mechanical keyboards let you change the switches?**
   Most hot-swap boards let you pull switches out and press new ones in with no soldering. A few budget boards have soldered switches you can't easily change, usually to keep the price down. Check the board's product page.

3. **What is a safe actuation force for everyday typing?**
   Usually 45 to 55 grams for most typists, with lighter 35-gram switches suited to fast, light presses. The right weight depends on your typing style. Try a switch tester before you commit to a full set.

[... 3 more, continuing the numbering]
```

---

## Notes for the builder

- This skill does NOT call any external MCP directly. It reads from `research-brief.md` which was populated by `research-flow.md`. If you need to test this skill standalone, hand-write a `research-brief.md` stub.
- Keep this skill's instructions tight. The first version of this skill in production should be roughly 250-400 lines. If it grows past 500, prune (Ryan Law's lesson — long skills are less reliably followed by the LLM).
- The hard checks at the bottom are the most important section. If you cut anything, do not cut the hard checks.
