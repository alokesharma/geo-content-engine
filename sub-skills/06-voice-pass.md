---
name: voice-pass
description: Quality gate that enforces content_rules.md hard rules programmatically on a drafted blog article. Strips forbidden phrases, em and en dashes, dramatic rhetorical setups, vague quantifiers when numbers are available, and verb-repetition for emphasis. Softens claim-denial language to safer phrasing. Checks structural monotony (4+ consecutive prose paragraphs flagged). Use after internal-linking and before seo-meta-builder. Triggers on "voice pass" or as part of content-gen-pipeline.
---

# voice-pass

Post-draft quality gate. Enforces every applicable hard rule from content_rules.md (the consolidated rule set (8 groups) including the v5 voice/quality additions #40-#50). Catches what the writer skill missed. Adds the structural monotony check that isn't in any other skill.

---

## When to use

After `draft.md`, `faq-builder.md`, and `internal-linking.md` have all run. Before `seo-meta-builder.md` because the meta description should be written against the cleaned voice, not the pre-clean draft.

---

## Inputs

- `draft-linked.md` (the article post-FAQ, post-internal-links)
- `content_rules.md` (the consolidated rule set (8 groups))

---

## Process

Run these checks in order. Each check produces either an automated fix or a flag for human revision. The skill prefers automated fix where the rule allows it; otherwise it flags.

### Step 0 — Run the executable validator (no self-grading)

**Run this BEFORE writing the QA status, and AGAIN after any auto-fixes.** The checks below describe what to look for, but the publish-blocking ones are enforced by an actual script so the QA block reports *executed* results, never the model's self-assessment (the v5 run self-reported "23/23 pass" while a `[Source: ...]` bracket and "clock starts" both survived).

```bash
pip install wordfreq textstat        # one-time; the validator uses these proven tools
python3 sub-skills/validate.py runs/<run-id>/draft-voice-passed.md --json \
        --brief runs/<run-id>/research-brief.md \
        --seo   runs/<run-id>/seo-meta.md \
        --run-folder runs/<run-id> \
        --ai-mode runs/<run-id>/ai-mode.json
```
(Pass `--brief` and `--seo` so the trace checks run too: meta-title-matches-topic (#58) and verbatim-keyword (#62). If seo-meta.md doesn't exist yet at this stage, run those two after seo-meta-builder; the article-level checks run regardless.)

- The script returns JSON with `overall` (PASS/FAIL), per-check status, and the exact offending lines. Exit code 1 means at least one FAIL.
- **It is publish-blocking.** If `overall` is FAIL, fix the flagged lines, then re-run until it returns PASS. Do NOT write a PASS into the QA block unless the script actually returned PASS.
- **The recurring offenders are now hard FAILs that block publish** (this is what stops the team re-flagging the same things): stray non-link `[..]` brackets, internal placeholders, merged citations, impossible metric labels, the metaphor family (clock/lever/bites), banned jargon and banned phrases. The pillar link is also a FAIL if missing.
- **The banned jargon/phrases/metaphors live in `sub-skills/style.json` — the team owns that file.** When a reviewer flags a new word or phrase that must never recur, add ONE line to that JSON and it becomes a blocking FAIL on the next run. No Python edit needed.
- `wordfreq` auto-FLAGS rare/hard words with zero maintenance (it catches NEW hard words the JSON doesn't list yet). Readability (textstat) and casual register are FLAGs. If `wordfreq`/`textstat` are missing the script marks those SKIPPED and prints an install hint — it never silently passes. If the optional `vale` binary is on PATH it runs as a bonus layer.
- Copy the script's `overall`, fail count, and flag count straight into the QA block's "Voice & canon" line. The script is the source of truth for that line.

The numbered checks below remain the reference for *what* each rule means and for the auto-fixes the validator does not perform (e.g. rewriting a flagged sentence). The validator is the *gate*; these are the *guidance*.

### Step 0a — Plain-English rewrite pass (v19, the CMO-feedback fix)

**The new layperson register pass.** Run this BEFORE Step 0b (heading check) and BEFORE Step 1 onwards. This is the single most important register lever in v19; without it, the draft stays in Claude's default writerly register no matter how many ban-lists we add. textstat passes things like "Three failure modes turn a brochure line into a rejected claim" because Flesch/FK count syllables, not register. This pass uses the LLM to *rewrite* for register, then `validate.py` re-runs to enforce the hygiene rules on the rewritten text.

**The pass is structured (not freeform "make it simpler"):**

**v22.6 — triage first, rewrite ONLY what fails (the blanket full-article rewrite is retired).** Run `validate.py` (Step 0) BEFORE this pass and keep its output open. Then, for each section (one at a time):

1. **Read the section against the checklist in point 2 and the v19 few-shot specimens** (in `03-draft.md`, the "v19 few-shot specimens" block). This READ applies to every section, every run — the same criteria as before, nothing is waved through.
2. **Identify register failures.** For every sentence ask:
   - Does it contain an abstract group noun (failure modes, edge cases, the small print, the headline, the asymmetry)? → rewrite to plain concrete language.
   - Does it use writerly cause-effect (*X turns Y into Z*, *flips the math*, *makes the math work*)? → rewrite to direct cause and effect (*Y happens because of X*).
   - Does it use narrator voice (*it's worth knowing*, *they're worth knowing before you file*, *the question that decides…*)? → delete the narrator clause; the reader already knows why they're reading.
   - Does it reference the document meta-textually (*the brochure*, *the brochure line*, *the small print*)? → replace with "the policy document" only when actually referring to a document; otherwise rewrite away.
   - Is the sentence too long, or compound-clausal? → split into shorter sentences (target ≤22-word average; hard cap 28).
   - Would the A1 reader (a 55-year-old, not a confident English reader, new to the topic) follow it? → if not, simplify words and structure.
3. **Rewrite ONLY the sections where step 2 found failures.** Preserve every fact and number; change only the register. A section with zero identified failures is left byte-identical — do not "polish" it. If NO section has failures and the validator's readability check already PASSes, record "register: clean, no rewrite needed" in `voice-pass-report.md` and move to Step 0a.1.
4. **Self-check the rewritten sections against the few-shot.** Does each rewritten section now read like Specimen 1-5 in `03-draft.md`? If a sentence would fit in v18.1 but not in the specimens, rewrite it again.

After the failing sections are rewritten, run `validate.py` once more. The plain-English pass should produce a draft where:
- `readability` (textstat) returns FK grade ≤ 7 and Flesch ≥ 70 (the v19 thresholds in `style.json`).
- `casual_patterns` and `metaphor_patterns` and `banned_phrases` continue to pass.
- The stakeholder test ("would my parent understand every sentence?") is the human gate — voice-pass is the machine support, not the final word on register.

**Why this is a write-time loop, not a single check.** Banning specific words fails (the LLM picks new ones). What works is rewriting the *output* in a tight register loop with a concrete reader persona and specimen paragraphs to imitate. This pass is that loop.

### Step 0a.1 — Anti-AI tell rewrite pass (v22-antiai, from WP:AISIGNS)

**This is the fork's defining addition.** After the plain-English rewrite, do a targeted pass for the "Signs of AI writing" tells now enforced by `validate.py` (canon Group I). For each, **don't just delete the trigger word — rewrite the sentence so it states the specific fact and drops the inflation.** The field guide's core insight: AI smooths a sharp fact into a generic, important-sounding blur; reverse it.

**v22.6 — work from the validator's line numbers, not a fresh full read.** The Step 0 validate output lists the exact offending line for every `ai_*` FAIL; fix those lines first. Then do ONE quick scan for the two literal tells the fix might have introduced (em/en dashes, curly quotes) as a find-replace. Only if the validator reported zero `ai_*` hits AND the scan is clean is this pass a no-op.

Apply these moves to each flagged line:

- **Copula back in** (`ai_copula`, FAIL): "The plan serves as a safety net / boasts wide coverage" → "The plan is a safety net / has wide coverage."
- **Kill the '-ing' tail** (`ai_ing_tail`, FAIL): "The app supports 8,000 locations, underscoring its reach." → "The app supports 8,000 locations." (Was the "reach" sourced? If not it was filler.)
- **Name the source or cut** (`ai_vague_attr`, FAIL): "Experts say the trial period is fair" → cite the primary source, or delete the sentence.
- **Un-parallel it** (`ai_neg_parallel`, FAIL): "It's not just a tool, it's peace of mind" → say what it actually does.
- **Inflated → specific** (`ai_puffery`, FAIL): "plays a vital role / a testament to / nestled in the heart of / enduring legacy" → the concrete fact, no importance-inflation.
- **Mechanical fixes** (`ai_dash`, `ai_curly`, FAIL — auto-fixable): em/en dashes → comma/colon/period; curly quotes/apostrophes (" " ' ') → straight ASCII (" '). Do these as a find-replace before re-validating.
- **AI vocabulary** (`banned_words`, FAIL): delve, underscore, tapestry, robust, leverage, seamless, showcase, vibrant, myriad, plethora, bolster, garner, intricate, meticulous → use the plain swap from `style.json`.
- **FLAG-level (review, don't block):** rule-of-three triplets ("vibrant, diverse, and dynamic" → keep one, or rewrite); knowledge-cutoff/"not documented" disclaimers (delete — they're speculative); the "Despite its X, faces challenges… / Future Prospects" outline close (rewrite to the one real constraint, or cut).

Then re-run `validate.py`. All `ai_*` FAIL checks must be clean. The FLAG ones are a human judgment call.

### 1. Forbidden phrase strip (Rule #8)

Regex match against the FORBIDDEN_PHRASES list in content_rules.md. Currently includes:
- "in conclusion", "it is important to note", "in today's fast-paced", "needless to say"
- "let us delve", "let's delve", "in this comprehensive", "without further ado"
- "navigating the complexities", "you'll learn", "we'll cover", "we'll explore"
- "let's explore", "let's look at", "this article will", "this guide covers", "in this article"

Any match: strip the phrase OR rewrite the surrounding sentence if the phrase carries necessary meaning. Hard fail if not strippable without breaking the sentence.

### 2. Em/en dash strip (Rule #12)

Replace every `—` and `–` with comma, colon, or full stop. Heuristic: if the dash separates an aside, use commas; if it introduces an explanation, use a colon; if it joins two complete clauses, use a full stop.

### 3. Vague quantifier audit (Rule #14)

Count occurrences of: "significant", "considerable", "substantial", "various", "numerous", "several", "many", "some", "a number of", "a variety of", "a range of".

- Total count >2 in the article: flag the densest paragraphs for revision
- For each occurrence, check if a specific number from research-brief is available. If yes, replace the quantifier with the number. If no, leave (hedging with "typically" is acceptable per Rule #14).

### 4. Rhetorical-setup strip (Rule #18)

Find and strip:
- "The catch is…"
- "The trap to watch…"
- "The one that catches [buyers/new users]…"
- "Knowing X is one thing. Knowing Y is another."
- "There are five." / "There are four." used as a dramatic standalone line
- "Binary" used to mean "either/or" dramatically
- "Almost certainly denied", "Will be voided", "Will be rejected"

These are pattern strips, not single-word strips. Identify the rhetorical construction, then rewrite that sentence in a flatter tone. Example:
- "The catch is that there isn't one setup step. There are five." → "Most setups take four to five steps, each for a different part of the process."

### 5. Verb-repetition check (Rule #19)

Find paragraphs where 2+ consecutive sentences start with the same imperative verb ("Read it once. Read it again."). Flag for revision. Auto-fix is possible by collapsing the sentences or converting to a bulleted checklist.

### 6. Reflective-close check (Rule #20)

Verify the last body section (before FAQ) is NOT a reflective philosophical paragraph re-stating the article's thesis. Common offender opening words: "Setup steps aren't a trick", "It's the cheapest way to plan ahead", "At the end of the day".

If found: strip the section entirely. Do NOT preserve it.

### 7. Claim-denial softening (Rule #21)

Find "denied", "rejected", "voided" used in body. Replace with safer phrasing:
- "your request will almost certainly be denied" → "the request would not be approved under the [specific policy/term]"
- "the account can be voided at any time" → "the provider can dispute the request under the [specific term]"

Do not soften "denied" / "rejected" if the article is specifically about historical cases or rejection statistics; context matters.

### 8. H2 length check (Rule #2)

Every H2 must be ≤10 words. Any H2 over 10 words: flag for revision (cannot be auto-shortened reliably).

### 9. Structural monotony check (NEW — Rule from data-lineage learnings)

Scan the body for 4+ consecutive paragraphs where ALL of these are true:
- Paragraph is prose (not a list, table, callout, or quote block)
- Paragraph is over 50 words

If such a run exists, flag it for revision with the suggestion to break it up with one of: bullet list (if items are parallel), table (if comparing options), callout (if one fact is screenshot-worthy), or sub-headings.

### 10. Lede throat-clearing check (Rule #13)

First sentence of the article must NOT start with: "In this", "This article", "Let's", "Today's", "Understanding [X] is", "In this comprehensive". If it does, hard fail with a request to rewrite the lede.

### 11. Key-Takeaways position check (Rule #17)

The Key Takeaways block must be the terminal section. If anything follows it other than a compliance/registration footer (if your domain needs one), flag for reordering.

### 12. Source-link enforcement on every stat (Rule #34) — publish-blocking

Scan the article for every numeric claim that comes from external research (statistics, study findings, survey numbers, regulatory figures). Each one MUST be followed by an inline `[Source: PublisherName]` attribution where PublisherName is a working hyperlink to the exact source URL.

- Any external stat without a `[Source: ...]` link = hard fail. Flag the exact sentence.
- **A source label with NO URL is a hard fail (run-1 bug).** "Source: [Publisher]" or "Source: Publisher" with no actual link does NOT pass. The publisher name must carry a real URL, written as a markdown link `[Publisher](https://publisher.example/specific-page)`. Pull the URL from `research-brief.md` §7 (data enrichment captured publisher + URL + date for every stat). If the URL is missing from the brief, the stat cannot be used.
- "Experts say" / "studies show" / "research indicates" without a named linked source = hard fail.
- Verify each link is well-formed (starts with https://) and points to a specific page, not a generic homepage.
- Numbers from brand internal data carry `[Source: brand internal data]` (no external link required) but must be team-verified, never invented.
- Numbers that are illustrative (e.g., a worked example's hypothetical $850 cost) are NOT external stats and do not require a source — but must read clearly as illustrative, not as a cited figure.

### 13. Readability check (textstat)

Run the article body through the `textstat` Python library (free, no API, no network). Install once: `pip install "textstat==0.7.3" pyphen --break-system-packages`. Compute Flesch Reading Ease, Flesch-Kincaid grade, and average sentence length on the body text (strip headings, tables, links first).

Surface ONE plain-language line in the QA block, not the raw indices:

> **Reading level: <grade> · Easy-to-read: <Easy / Medium / Hard> · <ship-ready / simplify / rewrite>**

Pass / flag / fail logic (tightened May 2026 — the 2026-05-21 run scored "Easy" yet read robotically; the floor was too low):
- Flesch Reading Ease ≥ 60 and FK grade ≤ 9 → **pass** ("ship-ready")
- Flesch Reading Ease 50–60 → **flag** ("acceptable, simplify the technical vocabulary; ties to Rules #37 and #42")
- Flesch Reading Ease < 50 → **hard fail** ("too difficult, rewrite")
- Average sentence length > 28 words → **hard fail** (ties to Rule #36)

textstat measures mechanical readability only (word/sentence length). It does NOT judge whether the writing is good — that stays the northstar's job, and the structural checks below (sections opening on a mechanism, robotic bridges) catch what textstat can't. This is a floor check, not a quality verdict.

*(Future upgrade: if Grammarly Enterprise API access is ever provisioned, its Writing Score API can replace textstat for richer clarity/engagement scores. Not available on the current Grammarly Business plan — textstat is the standing solution.)*

### 14. Plain-vocabulary check — Dale-Chall (canon Rule #42, replaces any banned-word list)

We do NOT keep a blacklist of hard words; it can't predict the next run. Instead, invert it: flag any word that is NOT on a list of *easy* words.

- Use the **Dale-Chall familiar-word list** (~3,000 everyday words) — available via `textstat`'s `dale_chall_readability_score` internals, or load the standard list directly (`pip install textstat`; the corpus ships with it). 
- Tokenise the body (strip headings, links, tables). For each content word (skip stopwords, proper nouns, numbers): if it is NOT in the familiar list AND NOT on the **domain glossary allow-list** below, surface it as a hard-word candidate with a suggested plain swap.
- Domain glossary allow-list (NOT flagged — these are glossed on first use per Rule #37, not removed): the team-maintained set of domain terms of art in `style.json` (e.g. for a SaaS/product domain: `SDK, API, webhook, SSO, uptime, latency, onboarding, sandbox`). Populate this list for your own vertical.
- Output: a list of `{word, sentence, suggested_swap}` for human revision. This is a **flag, not an auto-strip** (swaps can change meaning). Examples the gate would catch with no maintenance: "commencement → start", "annexed → attached", "nuanced → has exceptions", "arbitrary → without a clear rule".
- Escalation: if the same hard word appears 3+ times, raise it to a stronger flag — it's a tic, not a one-off.

### 15. Single-source citation enforcement (canon Rule #44) — publish-blocking

Scan every `[Source: …]`. A citation containing a `/`, `&`, `,`, or the word "and" between two publisher/report names is a **merged citation** = hard fail. Flag the exact citation (e.g. "[Business Standard / Government Report 2023-24]") and require it be reduced to one publisher + one URL.

### 16. Naked-bracket / literal-markdown strip (canon Rule #34, the run-2 bug) — publish-blocking

After link conversion, NO literal `[` or `]` may survive in body or citation text. "Source: [Publisher]" or "[Business Standard…]" with brackets showing is a hard fail. The publisher name must render as plain hyperlinked text with the brackets removed (the delivery step strips them; this check catches any that survive). Also fail any leftover raw markdown link syntax `[text](url)` in the rendered body.

### 17. Internal-placeholder leak (canon Rule #47) — publish-blocking

Any bracketed team-instruction in the body is a hard fail: `[brand internal data needed`, `[TBD]`, `[needed]`, `[team to supply]`, `[placeholder]`. These belong only in the "Team to supply" appendix. If found in body prose, fail and point to the exact sentence.

### 18. Statistic count + placement (canon Rules #43, #50)

- Count distinct externally-sourced statistics (each `[Source: …]` on a third-party number). **More than 1 = cut** (keep the single stat that most changes the reader's decision; v21 config external_stats_max: 1). Citations to a regulator or standards body's rules/clauses do not count.
- Locate the first external statistic. If it falls in the lede, stage-setter, or the first body section (before ~the third substantive paragraph), **flag** "stat rushed — move it deeper" (this was the 2026-05-21 paragraph-two dump).

### 19. Metric-label sanity (canon Rule #49) — publish-blocking

For each statistic, check the value against its stated metric name. A ratio >100% labelled as a percentage share (e.g. "satisfaction rate") is definitionally impossible = hard fail (the 2026-05-21 "103.38% rate" was actually a different index that can exceed 100%). Cross-check the label against research-brief §7 `exact_metric_name`; if the draft's label differs from the source's wording, fail and require the source's exact term.

### 20. Robotic-bridge / mechanism-opening check (canon Rules #3b, #40)

- **Bridge strip:** flag formulaic connective sentences between sections: "Knowing X is one thing. Knowing Y is another.", "X is half the story. Y is the other half.", "Categories are easier than mechanics.", "Here's how the process actually runs", "Now that you know X, the next question is Y." Auto-strippable when the section reads fine without them.
- **Mechanism-opening flag:** for each H2 section, check whether the first sentence opens on a mechanism/definition restatement ("The process starts on…", "The timer is measured from…") instead of the reader's question or decision. Flag for a situation-first rewrite.

### 21. Pillar-interlink presence (v20.5: validator also enforces link_count_max=4, no_forum_links, link_para_spacing -- see 05-internal-linking.md)

#### Original heading restored:
### 21. Pillar-interlink presence (canon Rule #45) — publish-blocking

Exactly one link whose anchor is the bare vertical name ("guides", "products", "pricing", or your configured vertical name) pointing to the pillar URL in `link_map.json` (v21 map: e.g. guides → /guides/, products → /products/, pricing → /pricing/). Skipped for service-topic articles. Missing = hard fail (coordinate with internal-linking, which inserts it). More than one pillar link = flag to dedupe.

### 22. Redundancy check (canon Rule #35)

Detect the same numeric+term pair (e.g. "30-day trial", "12-month contract") repeated in 3+ distinct sections. Flag the repeats for consolidation — state a fact once, reference it later, don't restate it. (The 2026-05-21 run repeated the same 30-day cap several times.)

### 23. Data-currency check (canon Rule #48)

For every statistic, verify the data vintage is stated inline ("in FY24…", "as of March 2024…"). A bare current-tense stat with no year, when the source is older than the article's publish year, is a flag — the reader must not assume a 2023-24 figure is current.

---

## Output

- `draft-voice-passed.md` — the cleaned article
- `voice-pass-report.md` — a markdown report listing every rule that triggered, what was stripped, and any items flagged for human revision rather than auto-stripped
- `voice-pass-status.json` with PASS / PARTIAL / FAIL + reasons

---

## Hard checks (publish-blocking)

- **`python3 sub-skills/validate.py <draft> --json` returns `overall: PASS` (zero FAILs). This is the executed gate; the rest of this list is enforced by it.**
- Zero forbidden phrases remaining (pruned list — throat-clearing only; specific roadmap lines pass)
- Zero em/en dashes remaining
- All H2s ≤10 words
- No reflective-close section between body and FAQ
- Key Takeaways is the terminal block
- Lede does not start with a throat-clearing pattern (one situational framing sentence is allowed, Rule #3a)
- Zero merged-publisher citations (check 15)
- Every Source link is a deep link to a specific page, never a domain homepage (check 12; validator `source_deeplink`, v22.1)
- Zero literal `[ ]` brackets or raw markdown links surviving in body (check 16)
- Zero internal-placeholder brackets in body prose (check 17)
- No statistic mislabelled against its value; metric name matches the source (check 19)
- Exactly one pillar interlink to `example.com/<vertical>/` (check 21)
- No more than 1 externally-sourced statistic (check 18; config external_stats_max: 1)
- **Anti-AI tells (v22-antiai, WP:AISIGNS) all clean:** zero copula avoidance (`ai_copula`), zero superficial '-ing' tails (`ai_ing_tail`), zero vague attribution (`ai_vague_attr`), zero negative parallelism (`ai_neg_parallel`), zero significance puffery (`ai_puffery`), zero em/en dashes (`ai_dash`), zero curly quotes (`ai_curly`)

---

## What it prevents

- Voice drift slipping past the writer skill
- AI tells in published content
- Structural monotony (everything as prose)
- Dramatic / legally-risky language
- The exact failure modes the team flagged in their v2 review

---

## Notes for the builder

- This skill's effectiveness depends on the forbidden-phrase list being maintained. When the team finds a new tic in published content, ADD it to FORBIDDEN_PHRASES in content_rules.md. This skill picks up the change on the next run.
- The "auto-fix vs flag" distinction matters. Auto-fix only where the fix is mechanical and lossless. Anywhere the fix is ambiguous, flag for human revision. Better to slow down than to silently change meaning.
- The structural monotony check (step 9) is the only NEW check this skill adds beyond what's in content_rules.md. It exists because v1/v2 articles were mostly prose; the team's "structural variety" critique landed exactly here.


## v20.6.4 R6 -- Batch all validator FAILs in ONE rewrite cycle (target -5-10min)

Old pattern: 5+ voice-pass iterations, each fixing 1-2 FAILs. Each iteration = full read + targeted rewrite + re-validate. Total: 10-15 minutes.

New pattern:
1. Run validate.py ONCE. Capture ALL FAILs + ALL FLAGs.
2. ONE rewrite pass addressing every issue at once.
3. Re-run validate.py with --cache-from previous result (skips already-passed checks per R4).
4. If clean -> done. If 1-2 FAILs remain -> ONE more targeted pass.

Cap: max 2 voice-pass iterations total (down from 5).
