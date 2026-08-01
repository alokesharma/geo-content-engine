> Example canon — replace with your own brand's rules.

# Content Rules, the canon

This file governs how every article is written. It applies to both Crawl-based and Brief-based articles. It is the source of truth; if anything in `northstar.md` or a prompt string contradicts this file, this file wins.

The whole document is built around one idea, the **Reader Contract**. Read it first; everything else is an application of it.

---

## 1. The Reader Contract

> **Every component of an article exists because the reader needs it here. Nothing exists because a checklist demanded it.**

A reader landed on this page with a real question. They are deciding whether to spend two minutes of their life on what we wrote. Each decision we make, to add a callout, to use a table instead of bullets, to break the page with an FAQ, must answer one question:

*Does this make the next 30 seconds of reading more useful, or am I just filling space?*

If you can't say what a section earns the reader, cut it. If a callout would interrupt a thought instead of punctuate it, leave it inline. If a comparison has only two dimensions, write it as a sentence; don't dress it as a table. **Composition over completeness.**

Three judgment calls that come up constantly:

- **Callout vs. inline emphasis.** A callout is for a fact the reader will hurt themselves by missing. *"The return window closes 30 days after delivery. Miss it and the item is non-refundable."* That earns a callout. *"Most orders ship within two days."* That's inline.
- **Table vs. bullets.** A table earns its space when there are ≥3 options or ≥4 dimensions, and the reader will scan across rows to compare. Two options with one difference each? A sentence with a semicolon does it.
- **FAQ block vs. body absorption.** An FAQ exists when 4+ residual questions remain after the body has done its job. If only two questions remain, fold them into the closing — don't pretend you have a bigger FAQ than you do.

If you find yourself adding something to satisfy a rule, stop and ask whether the rule serves the reader here. The rule is a default; the reader is the constraint.

---

## 2. Section choices (the section-tool reference)

Section types are tools. Use the right one for the question the section is answering, not the one that was next on a list.

| Tool | Earns its place when… |
|---|---|
| **content_block** (paragraph) | The reader needs explanation, story, or nuance. The default. |
| **bullet_list** | 3–6 parallel items the reader will scan, not read in order. ≤3 → write as prose; ≥7 → reorganise. |
| **comparison_table** | ≥3 options OR ≥4 dimensions, and the reader will compare across rows. Otherwise prose or bullets. |
| **callout** (info / tip / warning) | A single fact the reader will damage themselves by missing. Punctuation, not paragraphs. **Max ~3 per article; never adjacent.** |
| **steps** | A literal sequence the reader will execute. Not a synonym for "list of things." |
| **faq** | The fixed FAQ block. See F1. |

**Internal links**: max 4 per article (1 mandatory pillar + 3 contextual). v20.5 cap. Anchor text is the linked page's question or specific subject — never *"click here"* or *"learn more"*.

> **v20, what was removed from §2, and why.** The previous "Voice charter" with a worked example was a *writerly* anchor. It used "lever", "punchline", concession moves, the exact tics A2 bans. The model averaged the new register against that example and drifted writerly. Voice now lives entirely in A1 plus the few-shot specimens in `sub-skills/03-draft.md`. The §3 narrative spine ("Orient, Understand, Decide, Close") was also removed: it pushed the model to produce guides; we don't write guides. Composition guidance now lives in B1-B6 and the section-source rule (`02-outline.md`). Also removed: `expert_tip` and `cta` (conflicted with A3); "bold lead-ins on paragraphs >100 words" (contradicted D6's ≤80-word cap); "density alternation" (invited filler-by-variety).

---

## 3. The rules (consolidated)

> **Consolidation note (v9, May 2026):** the rule set was collapsed from 57 sprawling, partly-contradictory rules into the ~26 below, grouped by job. Nothing real was lost: six near-duplicate rules became one each, and dead/conflicting rules were removed (the mandatory opinionated brand verdict; the "| Brand" meta suffix; the mandatory 80-150-word stage-setter; mandatory bridge sentences). Items marked **[gate]** are enforced by `sub-skills/validate.py`; the rest are write-time judgment guided by `target_specimen.md`.

> **Hard-check note (v18, May 2026):** another batch of rules that used to be prose-only judgment is now enforced as deterministic checks in `validate.py`, so they can no longer silently slip: full product name in every heading (B2, no shorthand like "Basic Plan" for "Basic Support Plan", FAIL; team-editable via `product_name_trims` in `style.json`); intro ≤4 sentences (B3); per-sentence ≤28-word hard cap (D2/D6); FAQ count 5-7 (F1, FAIL); presence of Key Takeaways + compliance footer + "Last updated" line (B6/G2, FAIL); Key Takeaways is the terminal block (B6); callout budget ≤3 and never adjacent (G1); each cited stat states its data year (C2/G2). The principle is unchanged from v8 onward: if a rule matters, it lives as code, not as a sentence the model grades itself on.

> **Hard-check note (v19, May 2026):** the next batch, driven by the team's "too long, too complex, tangential sections" feedback on v18.1. Now enforced as code: **outline selection** by AI Mode weight × SERP frequency (Reddit/Quora cannot create sections, outline rules in `02-outline.md`); **no heading may name the regulator/authority** (FAIL); **at most 1 regulatory/authoritative-source mention** in the whole article (FAIL); **at most 1 external sourced statistic** per article (FAIL); **body ≤1,500 words** (FAIL); **per-section answer shape**, each section's first 1-2 sentences must deliver the answer shape its heading asks for, no narrative wind-up (FLAG, B4); **plain-English register**, voice anchor rewritten to a non-expert reader, FK ceiling lowered 9→7, "brochure" banned, dedicated plain-English rewrite pass in `06-voice-pass.md`. `target_specimen.md` is **retired**; the few-shot specimens in `03-draft.md` are the new voice reference.

> **v20, the subtraction release (May 2026).** v19 added new code checks but left old writerly anchors in the canon (the §2 voice charter, the worked example with "lever"/"punchline", the §3 narrative spine, the §3a "framing sentence allowed" loophole, the §4 `expert_tip`/`cta`/"bold lead-ins on paragraphs >100 words"/"density alternation" entries). The model averaged the new register against the old anchors and stayed writerly. v20 **deletes** those anchors and **tightens every ceiling**: body ≤800 words (was 1,500); each H2 section ≤120 words (new, FAIL); FAQ count in [4, 6] (was 5-7 range); Key Takeaways exactly 4 (was 5-6); intro ≤2 sentences (was 4); FK ≤7 is now a **FAIL** (was FLAG); answer-shape FAIL (was FLAG, classifier fixed to cover all heading shapes); glossary_required list, domain terms the article can't avoid must carry a parenthetical gloss on first body use; extended `ban_swaps` with writerly tics ("lever", "failure modes", "edge cases", "the asymmetry", "the mechanism"). Stage-setter slot (old B3) removed. D4 vague phrasing removed. No new phases, no new files, just code that catches what prose used to permit.

### Group A — Voice & register (educate, never sell)

A1. **Write for one specific reader: a non-expert encountering the topic for the first time** (v19, replaces "knowledgeable friend"). Plain, calm, second person, active verbs, short sentences, contractions fine. Grade-7 reading level. No abstract nouns ("failure modes," "edge cases," "the brochure line"), no writerly cause-effect ("X turns Y into Z"), no narrator voice ("it's worth knowing," "the headline benefit"). If the reader you imagined cannot follow a sentence, rewrite it. The few-shot specimens in `sub-skills/03-draft.md` are the calibration reference (this replaces the old `target_specimen.md`).
A2. **No copywriting tics** [gate]: no rhetorical setups ("the catch is", "the trap"), no personification ("the clock starts", "levers", "bites you"), no clever parallels ("not X, but Y"), no verb-repetition for emphasis, no dramatic punchlines, no philosophical reflective close, no narrative scene-setting openers. Say it straight.
A3. **Educate, never sell** [gate]: the goal is to inform, not to recommend the brand. No "the brand is the right choice", no "best/cheapest", no CTA pitch, no marketing stats, no product positioning. State facts; let the reader decide.
A4. **Plain refusal/denial language (v19)**: "your request won't be approved" or "the provider will not honour it" is the preferred form. The older formulation "the request would not be eligible under [clause]" is allowed but no longer the only acceptable phrasing; plainer wording is preferred when it reads more naturally to the reader described in A1. Either way: no alarmist verbs ("denied," "voided," "rejected outright").
A5. **No throat-clearing or forbidden phrases** [gate]: the lede's first sentence IS the answer. Banned-phrase list lives in `style.json`. One human framing sentence before the answer is allowed (not throat-clearing).
A6. **No em or en dashes** [gate]: use commas, colons, or full stops.

### Group B — Structure & headings

B1. **H1 = the consumer question, near-verbatim** [gate]. If the topic is a question, the H1 ends with "?".
B2. **H2s: question-shaped, Title Case, full standalone context, never a restatement of the H1** [gate]. Keep them tight by preference, but there is NO word-count cap: clarity and the full product name win over brevity. Default to a question ("What Does the Standard Plan Include?", not "The Standard Plan Includes These Things"). Each heading must make full sense alone, no dangling "this/these/the answer" ("Which Add-ons Change the Answer?" is half-baked; write "Which Add-ons Extend the Standard Plan?"). Name the entity, never euphemise ("What Does the Official Data Say?", not "the Source's"). **Use the full product name, never a trimmed shorthand** [gate, v18]: write "Standard Support Plan", not "Standard Plan"/"Standard". The shorthand-to-full-name map lives in `style.json` (`product_name_trims`) and is a FAIL. Title Case includes the part after a hyphen ("Non-Standard"). "How to…" headings may stay declarative.
B3. **BLUF, hard**: the article's FIRST sentence IS the answer [gate]. The whole intro is **at most 2 short sentences** [gate, v20] (was 3-4). No stage-setter, no "human framing sentence" before the answer — both retired in v20. The lede is the intro. If the lede alone doesn't orient, the lede is wrong, not too short.
B4. **Each section answers its own heading in the first 1-2 sentences** [gate, v19]. The answer shape must match the question shape: Yes/No question → Yes/No in sentence 1; "What is X?" → definition in sentence 1 ("X is …"); "How does X compare to Y?" → key difference up front; "When does X happen?" → name the condition first; "Why…?" → state the cause first. One short context clause before the answer is fine ("On the free tier you get five seats; on the paid tier you get more"), but never a multi-sentence narrative wind-up ("If you've been putting this off for a while, the question that decides…"). Cohesion comes from clean headings + direct openers, NOT manufactured bridge sentences.
B5. **Define before you do**: define the subject term before any procedural, comparative, or eligibility content.
B6. **Key Takeaways: exactly 4 items, terminal block** [gate, v20] (was 5-6 range). After the FAQ; no reflective close after it; only the compliance footer follows. **Each takeaway's bold lead-in must be a self-contained statement, not a teaser fragment** [gate]: "The standard plan covers off-hours support, with limits", NOT "Yes, with limits"; "Add-ons restore the excluded features", NOT "Add-ons close specific gaps". A reader scanning only the bold lead-ins should understand each point.

### Group C — Facts & sourcing (zero fabrication)

C1. **Every factual/numeric claim is real and traceable** [gate]: cite a real source or hedge ("typically"); never invent a figure.
C2. **Stat relevance gate, cut tangential data** [gate]. **Max 1 external statistic per article** [gate, v19]. A statistic may appear ONLY if it directly answers a reader sub-question. Placed in the section about its own subject, never before the third substantive paragraph, with the data vintage inline ("in 2024") and the source's exact metric name (never relabel one metric as a different one). State it once, no follow-up paragraph caveating the metric definition.
C3. **One publisher per citation** [gate]; never merge two sources ("X via / and / reported by Y").
C4. **External stats: authoritative/official sources only, one inline linked source each** [gate]. The publisher must be a recognised regulator, government body, standards org, or another official/authoritative source, NOT a secondary publisher or aggregator. Written `Source: [Publisher](url)` (single brackets; the delivery step strips them to a clean hyperlink). Brand-verified internal data needs no external source. "Experts say"/"studies show" without a named authoritative source is banned.
C5. **Verbatim keywords only** [gate]: every keyword used traces word-for-word to a real pulled source in `research-brief.md`; never synthesize a variant, never fake a research annotation.
C6. **No research-mechanism words or internal flags in body prose** [gate]: never write "Reddit"/"Quora"/"SerpAPI"/"Ahrefs"/"PAA", and never leave "[internal data needed]"/"[TBD]" in the article (those live in a Team-to-supply appendix).
C7. **Regulatory/authoritative source: at most ONE mention per article, inline only** [gate, v19]: cite the source once, inside a generic section, in 1-2 lines. NEVER as a section heading (FAIL). NEVER a second reference, even rephrased, drop it. If a second regulatory anchor is needed, use a dated circular or official URL without naming the authority or "the regulator" in body prose.
C8. **Evidence-first, not model-recall (v12 grounding gate).** Specific/substantive claims, numbers, named rules, concrete facts, "X% of…", durations, prices, must trace to a real research-brief source (competitor read, Forums, Reddit/Quora, AI Mode, stat, authoritative source). The draft tags each such claim with its source; the auditor/validator verifies the claim's key phrase or number appears in that source file. A specific claim with NO traceable source is flagged "model-recall, verify or source." General domain knowledge isn't banned, but specifics must be grounded. This shifts the article's substance from the LLM's memory to fetched evidence (competitor + Forums + AI Mode + stats).

### Group D — Plain language & scannability

D1. **Plain words first; gloss every domain term on first use** [gate, v20]. Swap jargon for everyday words ("commencement date" → "start date", "remittance" → "payment"), the swap list lives in `style.json` (`ban_swaps`). For domain terms the article cannot avoid, the first body occurrence must carry a parenthetical gloss, e.g. *"an add-on (an extra feature you pay for separately)"*. The required-gloss list lives in `style.json` (`glossary_required`); the validator FAILs the article if any listed term appears unglossed on first use.
D2. **Short units**: sentences <=~28 words [gate]; paragraphs <=3 sentences.
D3. **No vague quantifiers when a number exists** ("significant", "several", "many"...): use the number or rephrase.
D4. **Progressive disclosure (don't dump the manual)** [v20]: answer the question, then add only the depth that serves it. **Max one worked example per concept**; the rest are bullets, not paragraphs. Removed in v20: the "non-commodity element" framing (it invited the "extra value section" that became the bloat we're fixing).
D5. **Don't over-repeat** [gate]: no idea restated across sections, no single content word over-used (e.g. "pool" x11). State once, reference later.
D6. **Break up long blocks** [gate]: no single prose paragraph over ~80 words — split it into shorter paragraphs or bullets. Never a wall of prose; vary structure after a table or long block. (The validator FLAGs any paragraph over 80 words.)
D7. **Length = SERP-driven coverage (v21)** [gate]: there is no fixed word cap. Body length follows `length-target.json` — a band derived from the median competitor body length, with a `section_target` (median competitor H2 count). Hit `section_target` with real, grounded sections; **length is a byproduct of coverage, never a target.** Hard runaway ceiling **≤2,800 words** (FAIL). Per-section cap is dynamic (from `length-target.json`, ~120–300 words; FAIL) so a long guide can have deeper sections but none can bloat. Below the SERP band or below `section_target` = FLAG (too thin for the topic). Intro **≤2 sentences** (B3); FAQ count in [4, 6]; Key Takeaways exactly 4. Counted on prose only — headings, tables, blockquotes excluded. Anti-padding is enforced by the per-section cap + the grounding floor (every specific traces to research), not by a blunt total cap.

### Group E — The brand layer (minimal, fenced, factual)

E1. **Surface brand facts, never sell them** [gate]: include a brand data point ONLY when it is real and relevant, stated plainly (woven in or as a bullet), never as a verdict, recommendation, or pitch. No dedicated brand section. No inline "(Source: internal data)" tag in prose. If no brand data is available, omit it entirely.
E2. **The brand knowledge base is a category-scoped factual source**: if the KB is a set of sales-call scripts, use it only for the relevant content category, extract only feature/spec facts, present them as short bullets/chunks, and strip every pitch, upsell, and objection-handling line. Never mirror its salesy register.
E3. **Brand safety** [gate]: never associate the brand with a negative, defect, or complaint; never editorialize about the brand.
E4. **One quiet contextual brand link**, anchor = the topic/category phrase (e.g. "the standard plan"), not a CTA sentence; plus max 3 other internal links with descriptive anchors (never "click here", never a naked URL [gate]). **No internal link in the lede or first 2 paragraphs** [gate], the first link sits no earlier than paragraph 3 (a link in the opening lines reads odd).

### Group F — FAQ & answer blocks

F1. **FAQ: exactly 5** [gate, v20] (was 5-7 range). Real user questions from PAA/Reddit/Quora/Ahrefs, rendered as a NUMBERED list; each answer **150-300 characters** and **BLUF** (the first sentence directly answers the question), plain English, no regulatory document/circular numbers, phrased differently from the body. **No FAQ may restate a body section's content** — if a question is already answered in the body, drop it.

### Group G — Boxes, footer, freshness, GEO

G1. **Boxes/callouts earn their place** [gate]: max 3 per article, never adjacent; render as a styled standout block (not a plain paragraph). Reserve for a fact the reader is hurt by missing. **A callout must NOT repeat content already in the section**, if the fact is already in the prose, it doesn't earn a box (v20).
G2. **Footer & freshness**: every article carries your compliance/regulatory footer, an "as of [month, year]" note on any pricing/comparison, and a visible "Last updated: [month, year]" line near the top.
G3. **Durable GEO only**: no gimmicks (no llms.txt, no artificial chunking). Real cited data + clear structure + a BLUF aligned to Google's **AI Mode** answer (the reliable signal; AIO retired in v12 #76) are the strategy. **Signal not source: paraphrase only, no verbatim span over ~8 words may match the AI Mode text**, it shapes what the BLUF covers, never the wording.

### Group H — Domain facts (your category, kept verbatim)

> Replace these with the hard, easily-mis-stated facts of your own domain. They exist so the model states the tricky, error-prone details correctly every time. The examples below are placeholders.

H1. State the standing exception plainly; do not fold it into the general rule as if it were just another case.
H2. When a limit changed on a known date, give the current value and the date it took effect.
H3. Where a term applies differently to two tiers, name both ranges rather than a single blended figure.

### Group I — Anti-AI writing tells (v22-antiai, from Wikipedia WP:AISIGNS)

These are the "Signs of AI writing" rules baked into this fork. They overlap with Group A (voice) but are enforced as their own `validate.py` gates so they can't slip. **The fix is never just deleting the trigger word, restore the specific fact and cut the inflation** (the field guide's core point: AI smooths a sharp fact into a generic, important-sounding blur; reverse it).

I1. **No copula avoidance** [gate]: say *is / are / has*, not "serves as", "stands as", "boasts", "represents a shift", "marks a pivotal moment". ("The museum serves as the city's archive" -> "The museum is the city's archive.")
I2. **No superficial '-ing' significance tails** [gate]: never end a sentence with a vague participle clause like "..., highlighting its importance", "..., contributing to the region's growth", "..., ensuring efficiency". Cut it or make it a plain, sourced statement.
I3. **No vague attribution / weasel** [gate]: no "experts say", "observers note", "studies show", "it is widely regarded", "several sources". Name the source (authoritative/official per Group C) or drop the claim.
I4. **No negative parallelism** [gate]: no "not only ... but also", "it's not X, it's Y", "not X but rather Y". State the thing plainly.
I5. **No significance/legacy puffery** [gate]: no "plays a vital role", "a testament to", "rich tapestry/heritage", "nestled in the heart of", "enduring legacy", "evolving landscape", "deeply rooted", "reflects a broader". State the specific fact instead.
I6. **No em/en dashes, no curly quotes** [gate]: em/en dashes -> comma/colon/period (also Rule A6); curly quotes/apostrophes -> straight ASCII. Both auto-fixable in the voice pass.
I7. **AI-vocabulary words are banned-with-swaps** [gate]: delve, underscore, tapestry, robust, leverage, seamless, showcase, vibrant, myriad, plethora, bolster, garner, intricate, meticulous (see `style.json` `ban_swaps`). Use the plain swap.
I8. **Avoid these (FLAG, not block)**: rule-of-three triplets ("vibrant, diverse, and dynamic"); knowledge-cutoff/"not documented" disclaimers; the outline "Despite its X, faces challenges... / Future Prospects" close.

> The full pattern lists live in `sub-skills/style.json` (team-editable). The *why* behind each tell is Wikipedia:Signs of AI writing (WP:AISIGNS).

## 4. Calibration anchor

**v19, `target_specimen.md` is retired.** The previous anchors (a set of reference articles) all encoded a *writerly* register: clever cause-effect lines, narrator voice, abstract group nouns. Drafts mimicked that register, which reviewers read as "too complex for a layman." The specific reaction to a line like "Three failure modes turn a brochure promise into a rejected request" was the trigger for this change.

The new voice reference lives directly inside the draft skill: **the few-shot specimen paragraphs in `sub-skills/03-draft.md`**. Those paragraphs are calibrated to the A1 reader (a non-expert encountering the topic for the first time), grade-7 reading level, no abstract nouns, no narrator voice. They are the only voice reference the draft step should use.

The honest finding from v18.1 → v19: the gap is not structural, it is *register*. Plain everyday words. Short concrete sentences. State the answer, then add the detail. No commentary on the document ("the brochure says…"), no commentary on the topic ("they're worth knowing before you decide"). Just the answer the reader came for.

---

*End of canon. Anything not covered here defaults to the Reader Contract: serve the reader, cut the rest.*


> **v20.5 — main pipeline changes (June 2026).** Ports the headings-scraper v1.3.2 architecture into the full pipeline. section-sources.json retired (the fabrication surface from v20.1-v20.3). Replaced by noun_floor + question_shape checks in validate.py (v20.7: topic_anchor and topic_subject_presence retired -- simpler heading layer). AI Overview dropped entirely (AI Mode is the only AI signal). Ahrefs restored at limit=10 on both calls (matching-terms + matching-terms with terms=questions). SERP fetch num=20, filter social/forums, ceiling at 8 publishers, auto-fallback to AI Mode references. Max 4 links total per article (1 pillar + 3 contextual), no forum links, links >=1 paragraph apart. FAQ count [4, 6]. QA Block stripped to 3 sections (SEO Meta, Research Provenance, Heading Source). Heading Source computed deterministically by lineage auditor.
